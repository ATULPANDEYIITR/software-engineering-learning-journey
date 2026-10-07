'use strict';

/**
 * Design Patterns II: Strategy, Observer, Adapter
 *
 * JavaScript-specific implementation:
 * - Strategy: interchangeable merge-policy objects.
 * - Observer: event-driven Pull Request lifecycle notifications.
 * - Adapter: normalization of an external CI API into the application's
 *   internal status contract.
 *
 * This file uses Node.js standard language features and requires no packages.
 */

// -----------------------------------------------------------------------------
// Domain types
// -----------------------------------------------------------------------------

const PullRequestState = Object.freeze({
  DRAFT: 'draft',
  OPEN: 'open',
  CHANGES_REQUESTED: 'changes_requested',
  MERGED: 'merged',
  CLOSED: 'closed'
});

const ReviewDecision = Object.freeze({
  APPROVE: 'approve',
  REQUEST_CHANGES: 'request_changes',
  COMMENT: 'comment'
});

const CheckStatus = Object.freeze({
  PASSING: 'passing',
  FAILING: 'failing',
  PENDING: 'pending'
});

class PullRequest {
  constructor({ number, title, author, sourceBranch, targetBranch, commits }) {
    if (!Number.isInteger(number) || number <= 0) {
      throw new TypeError('Pull Request number must be a positive integer.');
    }

    if (!Array.isArray(commits) || commits.length === 0) {
      throw new Error('A Pull Request requires at least one commit.');
    }

    this.number = number;
    this.title = title;
    this.author = author;
    this.sourceBranch = sourceBranch;
    this.targetBranch = targetBranch;
    this.commits = [...commits];
    this.state = PullRequestState.OPEN;
    this.reviews = [];
    this.statusChecks = [];
    this.mergeable = true;
  }

  get headSha() {
    return this.commits[this.commits.length - 1].sha;
  }

  addCommit(commit) {
    if (this.state === PullRequestState.MERGED ||
        this.state === PullRequestState.CLOSED) {
      throw new Error('Cannot add commits to a closed or merged Pull Request.');
    }

    if (!commit?.sha || !commit?.message) {
      throw new TypeError('A commit requires sha and message.');
    }

    this.commits.push({ ...commit });
  }

  addReview(review) {
    if (this.state === PullRequestState.MERGED ||
        this.state === PullRequestState.CLOSED) {
      throw new Error('Cannot review a closed or merged Pull Request.');
    }

    if (!review?.reviewer || !review?.decision || !review?.commitSha) {
      throw new TypeError('Review requires reviewer, decision, and commitSha.');
    }

    this.reviews.push({ ...review });
  }

  addStatusCheck(check) {
    if (!check?.name || !check?.status || !check?.commitSha) {
      throw new TypeError('Status check requires name, status, and commitSha.');
    }

    this.statusChecks.push({ ...check });
  }
}

// -----------------------------------------------------------------------------
// Strategy pattern
// -----------------------------------------------------------------------------

class MergeStrategy {
  evaluate(_pullRequest) {
    throw new Error('MergeStrategy.evaluate() must be implemented.');
  }
}

class DevelopmentBranchStrategy extends MergeStrategy {
  evaluate(pullRequest) {
    const reasons = [];

    if (pullRequest.state !== PullRequestState.OPEN) {
      reasons.push('Pull Request is not open.');
    }

    const currentChecks = pullRequest.statusChecks.filter(
      check => check.commitSha === pullRequest.headSha
    );

    if (currentChecks.length === 0) {
      reasons.push('No current status checks are available.');
    } else if (currentChecks.some(check => check.status !== CheckStatus.PASSING)) {
      reasons.push('At least one current status check is not passing.');
    }

    if (pullRequest.reviews.some(
      review =>
        review.commitSha === pullRequest.headSha &&
        review.decision === ReviewDecision.REQUEST_CHANGES
    )) {
      reasons.push('Current commit has an outstanding change request.');
    }

    if (!pullRequest.mergeable) {
      reasons.push('Pull Request contains unresolved conflicts.');
    }

    return {
      allowed: reasons.length === 0,
      reasons
    };
  }
}

class ProductionBranchStrategy extends MergeStrategy {
  constructor({ eligibleReviewers, requiredApprovals }) {
    super();

    if (!Number.isInteger(requiredApprovals) || requiredApprovals < 1) {
      throw new RangeError('requiredApprovals must be at least one.');
    }

    this.eligibleReviewers = new Set(eligibleReviewers);
    this.requiredApprovals = requiredApprovals;
  }

  evaluate(pullRequest) {
    const reasons = [];

    if (pullRequest.state !== PullRequestState.OPEN) {
      reasons.push('Pull Request is not open.');
    }

    const currentApprovals = new Set(
      pullRequest.reviews
        .filter(
          review =>
            review.commitSha === pullRequest.headSha &&
            review.decision === ReviewDecision.APPROVE &&
            this.eligibleReviewers.has(review.reviewer)
        )
        .map(review => review.reviewer)
    );

    if (currentApprovals.size < this.requiredApprovals) {
      reasons.push(
        `${this.requiredApprovals} eligible approvals required; ` +
        `${currentApprovals.size} available.`
      );
    }

    if (pullRequest.reviews.some(
      review =>
        review.commitSha === pullRequest.headSha &&
        review.decision === ReviewDecision.REQUEST_CHANGES
    )) {
      reasons.push('Current commit has a change request.');
    }

    const currentChecks = pullRequest.statusChecks.filter(
      check => check.commitSha === pullRequest.headSha
    );

    if (currentChecks.length === 0) {
      reasons.push('No current status checks are available.');
    } else if (currentChecks.some(check => check.status !== CheckStatus.PASSING)) {
      reasons.push('A current status check is failing or pending.');
    }

    if (!pullRequest.mergeable) {
      reasons.push('Pull Request contains unresolved conflicts.');
    }

    return {
      allowed: reasons.length === 0,
      reasons
    };
  }
}

// -----------------------------------------------------------------------------
// Observer pattern
// -----------------------------------------------------------------------------

class EventEmitter {
  constructor() {
    this.listeners = new Map();
  }

  on(eventName, listener) {
    if (typeof listener !== 'function') {
      throw new TypeError('Observer must be a function.');
    }

    if (!this.listeners.has(eventName)) {
      this.listeners.set(eventName, new Set());
    }

    this.listeners.get(eventName).add(listener);

    // Returning an unsubscribe function is useful in event-driven systems
    // because observers often have a lifecycle shorter than the publisher.
    return () => this.off(eventName, listener);
  }

  off(eventName, listener) {
    const listeners = this.listeners.get(eventName);

    if (!listeners) {
      return;
    }

    listeners.delete(listener);

    if (listeners.size === 0) {
      this.listeners.delete(eventName);
    }
  }

  emit(eventName, payload) {
    const listeners = this.listeners.get(eventName);

    if (!listeners) {
      return;
    }

    for (const listener of [...listeners]) {
      try {
        listener(payload);
      } catch (error) {
        // An observer failure should not prevent independent observers from
        // processing the same domain event.
        console.error(
          `[observer-error] ${eventName}: ${error.message}`
        );
      }
    }
  }
}

class AuditObserver {
  constructor() {
    this.entries = [];
  }

  handle(event) {
    const entry =
      `${event.type}: PR #${event.pullRequestNumber} by ${event.actor} - ` +
      event.message;

    this.entries.push(entry);
    console.log(`[audit] ${entry}`);
  }
}

class MetricsObserver {
  constructor() {
    this.counts = new Map();
  }

  handle(event) {
    this.counts.set(
      event.type,
      (this.counts.get(event.type) ?? 0) + 1
    );
  }
}

class NotificationObserver {
  handle(event) {
    if (event.type === 'review_requested') {
      console.log(
        `[notification] Reviewer ${event.reviewer} requested for ` +
        `PR #${event.pullRequestNumber}.`
      );
    }

    if (event.type === 'changes_requested') {
      console.log(
        `[notification] Changes requested on PR #${event.pullRequestNumber}.`
      );
    }
  }
}

// -----------------------------------------------------------------------------
// Adapter pattern
// -----------------------------------------------------------------------------

class ExternalCiClient {
  constructor() {
    this.builds = new Map([
      ['abc123', { id: 'ci-1001', result: 'SUCCESS', revision: 'abc123' }],
      ['def456', { id: 'ci-1002', result: 'FAILURE', revision: 'def456' }]
    ]);
  }

  async fetchBuild(revision) {
    // Promise-based API represents the asynchronous nature of many external
    // JavaScript integrations without requiring a third-party package.
    await Promise.resolve();

    return this.builds.get(revision) ?? null;
  }
}

class CiStatusAdapter {
  constructor(externalClient) {
    this.externalClient = externalClient;
  }

  async getStatus(commitSha) {
    const build = await this.externalClient.fetchBuild(commitSha);

    if (!build) {
      return {
        name: 'external-ci',
        status: CheckStatus.PENDING,
        commitSha
      };
    }

    const statusMap = {
      SUCCESS: CheckStatus.PASSING,
      FAILURE: CheckStatus.FAILING,
      CANCELLED: CheckStatus.FAILING
    };

    return {
      name: `external-ci/${build.id}`,
      status: statusMap[build.result] ?? CheckStatus.PENDING,
      commitSha
    };
  }
}

// -----------------------------------------------------------------------------
// Application service
// -----------------------------------------------------------------------------

class RepositoryGovernanceService {
  constructor({ strategy, statusProvider, eventBus }) {
    this.strategy = strategy;
    this.statusProvider = statusProvider;
    this.eventBus = eventBus;
  }

  requestReview(pullRequest, actor, reviewer) {
    this.eventBus.emit('review_requested', {
      type: 'review_requested',
      pullRequestNumber: pullRequest.number,
      actor,
      reviewer,
      message: `Review requested from ${reviewer}.`
    });
  }

  async synchronizeCiStatus(pullRequest, actor) {
    const status = await this.statusProvider.getStatus(pullRequest.headSha);

    pullRequest.addStatusCheck(status);

    this.eventBus.emit('status_updated', {
      type: 'status_updated',
      pullRequestNumber: pullRequest.number,
      actor,
      message: `${status.name} is ${status.status}.`
    });
  }

  submitReview(pullRequest, reviewer, decision, comment = '') {
    pullRequest.addReview({
      reviewer,
      decision,
      commitSha: pullRequest.headSha,
      comment
    });

    const eventType =
      decision === ReviewDecision.REQUEST_CHANGES
        ? 'changes_requested'
        : 'review_submitted';

    this.eventBus.emit(eventType, {
      type: eventType,
      pullRequestNumber: pullRequest.number,
      actor: reviewer,
      message: `${reviewer} submitted ${decision}.`
    });
  }

  evaluate(pullRequest) {
    return this.strategy.evaluate(pullRequest);
  }

  merge(pullRequest, actor) {
    const decision = this.evaluate(pullRequest);

    if (!decision.allowed) {
      console.log('[merge] blocked');

      for (const reason of decision.reasons) {
        console.log(`  - ${reason}`);
      }

      return false;
    }

    pullRequest.state = PullRequestState.MERGED;

    this.eventBus.emit('merged', {
      type: 'merged',
      pullRequestNumber: pullRequest.number,
      actor,
      message: 'Pull Request merged.'
    });

    return true;
  }
}

// -----------------------------------------------------------------------------
// Demonstration
// -----------------------------------------------------------------------------

function createPullRequest() {
  return new PullRequest({
    number: 84,
    title: 'Introduce resilient payment authorization',
    author: 'alice',
    sourceBranch: 'feature/payment-auth',
    targetBranch: 'main',
    commits: [
      {
        sha: 'abc123',
        message: 'Add payment authorization rules'
      }
    ]
  });
}

async function main() {
  console.log('=== Strategy ===');

  const pullRequest = createPullRequest();

  const developmentStrategy = new DevelopmentBranchStrategy();
  const productionStrategy = new ProductionBranchStrategy({
    eligibleReviewers: ['bob', 'carol', 'david'],
    requiredApprovals: 2
  });

  pullRequest.addStatusCheck({
    name: 'unit-tests',
    status: CheckStatus.PASSING,
    commitSha: pullRequest.headSha
  });

  pullRequest.addReview({
    reviewer: 'bob',
    decision: ReviewDecision.APPROVE,
    commitSha: pullRequest.headSha
  });

  console.log(
    'Development:',
    developmentStrategy.evaluate(pullRequest)
  );

  console.log(
    'Production:',
    productionStrategy.evaluate(pullRequest)
  );

  console.log('\n=== Observer + Adapter ===');

  const eventBus = new EventEmitter();
  const audit = new AuditObserver();
  const metrics = new MetricsObserver();
  const notifications = new NotificationObserver();

  eventBus.on('review_requested', event => audit.handle(event));
  eventBus.on('review_requested', event => notifications.handle(event));
  eventBus.on('review_submitted', event => audit.handle(event));
  eventBus.on('changes_requested', event => {
    audit.handle(event);
    notifications.handle(event);
  });
  eventBus.on('status_updated', event => audit.handle(event));
  eventBus.on('merged', event => audit.handle(event));

  // Subscribe the metrics observer to all lifecycle events without coupling
  // the publisher to any particular metric implementation.
  for (const eventType of [
    'review_requested',
    'review_submitted',
    'changes_requested',
    'status_updated',
    'merged'
  ]) {
    eventBus.on(eventType, event => metrics.handle(event));
  }

  const externalCi = new ExternalCiClient();
  const adapter = new CiStatusAdapter(externalCi);

  const service = new RepositoryGovernanceService({
    strategy: developmentStrategy,
    statusProvider: adapter,
    eventBus
  });

  service.requestReview(pullRequest, 'alice', 'bob');

  await service.synchronizeCiStatus(pullRequest, 'ci-bot');

  service.submitReview(
    pullRequest,
    'bob',
    ReviewDecision.APPROVE,
    'Authorization boundary is explicit.'
  );

  console.log('Merge decision:', service.evaluate(pullRequest));

  service.merge(pullRequest, 'release-bot');

  console.log('\nMetrics:');
  console.table(Object.fromEntries(metrics.counts));

  console.log('\n=== Adapter missing-build behavior ===');

  const unknownStatus = await adapter.getStatus('unknown-sha');
  console.log(unknownStatus);
}

main().catch(error => {
  console.error('Application failure:', error.message);
  process.exitCode = 1;
});
