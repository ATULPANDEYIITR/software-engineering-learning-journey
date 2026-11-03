'use strict';

const assert = require('node:assert/strict');

const PRState = Object.freeze({
    DRAFT: 'draft',
    OPEN: 'open',
    CLOSED: 'closed',
    MERGED: 'merged'
});

const ReviewState = Object.freeze({
    COMMENTED: 'commented',
    APPROVED: 'approved',
    CHANGES_REQUESTED: 'changes_requested',
    DISMISSED: 'dismissed'
});

const MergeStrategy = Object.freeze({
    MERGE_COMMIT: 'merge_commit',
    SQUASH: 'squash',
    REBASE: 'rebase'
});

class IntegrationError extends Error {}

class Repository {
    constructor(name) {
        this.name = name;
        this.branches = new Map();
        this.pullRequests = new Map();
        this.protection = new Map();
        this.nextPR = 1;
        this.events = [];
    }

    addBranch(name, commits = []) {
        if (this.branches.has(name)) {
            throw new IntegrationError(`Branch already exists: ${name}`);
        }

        this.branches.set(name, {
            name,
            commits: [...commits],
            protected: false
        });
    }

    protectBranch(name, policy) {
        const branch = this.branches.get(name);

        if (!branch) {
            throw new IntegrationError(`Unknown branch: ${name}`);
        }

        branch.protected = true;
        this.protection.set(name, {
            requiredReviews: policy.requiredReviews ?? 2,
            requiredChecks: new Set(policy.requiredChecks ?? []),
            requireConversationsResolved:
                policy.requireConversationsResolved ?? true,
            allowDirectPush: policy.allowDirectPush ?? false,
            allowForcePush: policy.allowForcePush ?? false
        });
    }

    commit(branchName, sha, message) {
        const branch = this.branches.get(branchName);

        if (!branch) {
            throw new IntegrationError(`Unknown branch: ${branchName}`);
        }

        if (!/^[0-9a-f]{7,40}$/i.test(sha)) {
            throw new IntegrationError('Invalid commit SHA');
        }

        if (!message || !message.trim()) {
            throw new IntegrationError('Commit message cannot be empty');
        }

        const commit = {
            sha,
            message: message.trim(),
            branch: branchName
        };

        branch.commits.push(commit);
        this.events.push({
            type: 'commit_created',
            branch: branchName,
            sha
        });

        return commit;
    }

    createPullRequest({
        title,
        source,
        target,
        author,
        changedFiles,
        draft = false
    }) {
        if (!this.branches.has(source) || !this.branches.has(target)) {
            throw new IntegrationError('Source and target branches must exist');
        }

        if (source === target) {
            throw new IntegrationError('Source and target cannot be identical');
        }

        const commits = [...this.branches.get(source).commits];

        if (commits.length === 0) {
            throw new IntegrationError(
                'A Pull Request must contain at least one commit'
            );
        }

        const pr = {
            number: this.nextPR++,
            title: title.trim(),
            source,
            target,
            author,
            state: draft ? PRState.DRAFT : PRState.OPEN,
            draft,
            commits,
            changedFiles: new Set(changedFiles),
            reviews: [],
            checks: [],
            conversations: [],
            mergeStrategy: null
        };

        this.pullRequests.set(pr.number, pr);

        this.events.push({
            type: 'pull_request_opened',
            number: pr.number,
            source,
            target
        });

        return pr;
    }

    synchronize(prNumber) {
        const pr = this.getPR(prNumber);
        pr.commits = [...this.branches.get(pr.source).commits];

        for (const review of pr.reviews) {
            if (review.commitSha !== this.latestCommit(pr)) {
                review.state = ReviewState.DISMISSED;
            }
        }

        this.events.push({
            type: 'pull_request_synchronized',
            number: prNumber,
            latestCommit: this.latestCommit(pr)
        });
    }

    getPR(number) {
        const pr = this.pullRequests.get(number);

        if (!pr) {
            throw new IntegrationError(`Unknown Pull Request #${number}`);
        }

        return pr;
    }

    latestCommit(pr) {
        return pr.commits.at(-1)?.sha ?? null;
    }

    addReview(prNumber, reviewer, state, commitSha, comment = '') {
        const pr = this.getPR(prNumber);

        if (reviewer === pr.author) {
            throw new IntegrationError(
                'Pull Request authors cannot approve their own changes'
            );
        }

        pr.reviews.push({
            reviewer,
            state,
            commitSha,
            comment,
            resolved: true
        });

        this.events.push({
            type: 'review_submitted',
            number: prNumber,
            reviewer,
            state
        });
    }

    resolveConversation(prNumber, reviewer) {
        const pr = this.getPR(prNumber);

        for (const conversation of pr.conversations) {
            if (conversation.reviewer === reviewer) {
                conversation.resolved = true;
            }
        }
    }

    addConversation(prNumber, reviewer, text) {
        if (!text.trim()) {
            throw new IntegrationError('Conversation text cannot be empty');
        }

        const pr = this.getPR(prNumber);

        pr.conversations.push({
            reviewer,
            text: text.trim(),
            resolved: false
        });
    }

    addStatusCheck(prNumber, name, passed, commitSha) {
        const pr = this.getPR(prNumber);

        pr.checks.push({
            name,
            passed: Boolean(passed),
            commitSha
        });
    }

    mergeEligibility(prNumber) {
        const pr = this.getPR(prNumber);
        const policy = this.protection.get(pr.target);
        const reasons = [];

        if (!policy) {
            reasons.push('Target branch has no branch-protection policy');
            return { eligible: false, reasons };
        }

        if (pr.state !== PRState.OPEN) {
            reasons.push('Pull Request is not open');
        }

        if (pr.draft) {
            reasons.push('Pull Request remains a draft');
        }

        const latest = this.latestCommit(pr);

        const approvals = new Set(
            pr.reviews
                .filter(review =>
                    review.state === ReviewState.APPROVED &&
                    review.commitSha === latest
                )
                .map(review => review.reviewer)
        );

        if (approvals.size < policy.requiredReviews) {
            reasons.push(
                `Requires ${policy.requiredReviews} current approval(s); ` +
                `found ${approvals.size}`
            );
        }

        for (const requiredCheck of policy.requiredChecks) {
            const validCheck = pr.checks.some(check =>
                check.name === requiredCheck &&
                check.commitSha === latest &&
                check.passed
            );

            if (!validCheck) {
                reasons.push(`Required status check failed: ${requiredCheck}`);
            }
        }

        if (
            policy.requireConversationsResolved &&
            pr.conversations.some(conversation => !conversation.resolved)
        ) {
            reasons.push('Unresolved review conversations remain');
        }

        if (pr.changedFiles.size === 0) {
            reasons.push('No files were changed');
        }

        return {
            eligible: reasons.length === 0,
            reasons
        };
    }

    merge(prNumber, strategy) {
        const result = this.mergeEligibility(prNumber);

        if (!result.eligible) {
            throw new IntegrationError(
                `Merge rejected: ${result.reasons.join('; ')}`
            );
        }

        const pr = this.getPR(prNumber);
        const target = this.branches.get(pr.target);

        if (strategy === MergeStrategy.MERGE_COMMIT) {
            target.commits.push({
                sha: `merge${String(pr.number).padStart(4, '0')}`,
                message: `Merge PR #${pr.number}: ${pr.title}`,
                branch: pr.target
            });
        } else if (strategy === MergeStrategy.SQUASH) {
            target.commits.push({
                sha: `squash${String(pr.number).padStart(4, '0')}`,
                message: pr.title,
                branch: pr.target
            });
        } else if (strategy === MergeStrategy.REBASE) {
            target.commits.push(
                ...pr.commits.map(commit => ({
                    ...commit,
                    branch: pr.target
                }))
            );
        } else {
            throw new IntegrationError('Unsupported merge strategy');
        }

        pr.state = PRState.MERGED;
        pr.mergeStrategy = strategy;

        this.events.push({
            type: 'pull_request_merged',
            number: prNumber,
            strategy
        });

        return target.commits.at(-1).sha;
    }
}

function testSuccessfulIntegrationWorkflow() {
    const repo = new Repository('integration-testing-demo');

    repo.addBranch('main', [{
        sha: '1111111',
        message: 'Initial release',
        branch: 'main'
    }]);

    repo.addBranch('feature/integration');

    repo.protectBranch('main', {
        requiredReviews: 2,
        requiredChecks: ['api-integration', 'database-integration'],
        requireConversationsResolved: true
    });

    repo.commit(
        'feature/integration',
        '2222222',
        'Add API and database integration tests'
    );

    const pr = repo.createPullRequest({
        title: 'Add database and API integration testing',
        source: 'feature/integration',
        target: 'main',
        author: 'alice',
        changedFiles: [
            'test/api.integration.js',
            'test/database.integration.js'
        ]
    });

    const latest = repo.latestCommit(pr);

    repo.addReview(pr.number, 'bob', ReviewState.APPROVED, latest);
    repo.addReview(pr.number, 'carol', ReviewState.APPROVED, latest);

    repo.addStatusCheck(
        pr.number,
        'api-integration',
        true,
        latest
    );

    repo.addStatusCheck(
        pr.number,
        'database-integration',
        true,
        latest
    );

    repo.addConversation(
        pr.number,
        'bob',
        'Please document rollback behavior.'
    );

    let eligibility = repo.mergeEligibility(pr.number);
    assert.equal(eligibility.eligible, false);

    repo.resolveConversation(pr.number, 'bob');

    eligibility = repo.mergeEligibility(pr.number);
    assert.equal(eligibility.eligible, true);

    const mergedSha = repo.merge(
        pr.number,
        MergeStrategy.SQUASH
    );

    assert.equal(pr.state, PRState.MERGED);
    assert.match(mergedSha, /^squash/);
}

function testStaleApproval() {
    const repo = new Repository('stale-approval-demo');

    repo.addBranch('main');
    repo.addBranch('feature');
    repo.protectBranch('main', {
        requiredReviews: 2,
        requiredChecks: ['integration-tests']
    });

    repo.commit('feature', '2222222', 'Initial test implementation');

    const pr = repo.createPullRequest({
        title: 'Integration test suite',
        source: 'feature',
        target: 'main',
        author: 'alice',
        changedFiles: ['integration.test.js']
    });

    const firstCommit = repo.latestCommit(pr);

    repo.addReview(
        pr.number,
        'bob',
        ReviewState.APPROVED,
        firstCommit
    );

    repo.addReview(
        pr.number,
        'carol',
        ReviewState.APPROVED,
        firstCommit
    );

    repo.commit(
        'feature',
        '3333333',
        'Fix database transaction rollback test'
    );

    repo.synchronize(pr.number);

    repo.addStatusCheck(
        pr.number,
        'integration-tests',
        true,
        '3333333'
    );

    const eligibility = repo.mergeEligibility(pr.number);

    assert.equal(eligibility.eligible, false);
    assert.ok(
        eligibility.reasons.some(reason =>
            reason.includes('current approval')
        )
    );
}

function run() {
    const tests = [
        ['successful integration workflow', testSuccessfulIntegrationWorkflow],
        ['stale approval handling', testStaleApproval]
    ];

    for (const [name, test] of tests) {
        try {
            test();
            console.log(`PASS: ${name}`);
        } catch (error) {
            console.error(`FAIL: ${name}`);
            console.error(error.message);
            process.exitCode = 1;
        }
    }
}

run();
