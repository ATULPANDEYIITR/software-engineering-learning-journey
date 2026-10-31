'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { EventEmitter } = require('node:events');

class UserRepository {
  constructor() {
    this.users = new Map();
  }

  async save(user) {
    if (!Number.isInteger(user.id) || user.id <= 0) {
      throw new TypeError('id must be a positive integer');
    }
    if (!user.name?.trim()) {
      throw new TypeError('name is required');
    }
    if (!isValidEmail(user.email)) {
      throw new TypeError('invalid email');
    }
    if (this.users.has(user.id)) {
      throw new Error('user already exists');
    }

    this.users.set(user.id, Object.freeze({ ...user }));
  }

  async findById(id) {
    return this.users.get(id) ?? null;
  }
}

function isValidEmail(email) {
  return typeof email === 'string' &&
    email.includes('@') &&
    email.split('@')[1]?.includes('.') &&
    !/\s/.test(email);
}

function calculateDiscount(total, percentage) {
  if (!Number.isFinite(total) || total < 0) {
    throw new RangeError('total must be non-negative');
  }
  if (!Number.isFinite(percentage) || percentage < 0 || percentage > 100) {
    throw new RangeError('percentage must be between 0 and 100');
  }
  return Math.round(total * (1 - percentage / 100) * 100) / 100;
}

class UserService extends EventEmitter {
  constructor(repository) {
    super();
    this.repository = repository;
  }

  async register(user) {
    await this.repository.save(user);
    this.emit('userRegistered', user);
    return user;
  }

  async getUser(id) {
    const user = await this.repository.findById(id);
    if (!user) {
      throw new Error(`user ${id} not found`);
    }
    return user;
  }

  async exportUser(id, directory) {
    const user = await this.getUser(id);
    await fs.mkdir(directory, { recursive: true });

    const output = path.join(directory, `user-${id}.json`);
    await fs.writeFile(
      output,
      JSON.stringify(user, null, 2),
      { encoding: 'utf8', flag: 'wx' }
    );

    return output;
  }
}

async function unitTests() {
  assert.equal(isValidEmail('person@example.com'), true);
  assert.equal(isValidEmail('person@example'), false);
  assert.equal(isValidEmail('person example.com'), false);

  assert.equal(calculateDiscount(1000, 25), 750);
  assert.equal(calculateDiscount(1000, 0), 1000);
  assert.equal(calculateDiscount(1000, 100), 0);

  assert.throws(() => calculateDiscount(-1, 10), RangeError);
  assert.throws(() => calculateDiscount(100, 101), RangeError);
}

async function integrationTests() {
  const repository = new UserRepository();
  const service = new UserService(repository);

  const events = [];
  service.on('userRegistered', user => events.push(user.id));

  const user = {
    id: 1,
    name: 'Atul',
    email: 'atul@example.com'
  };

  await service.register(user);

  assert.deepEqual(await repository.findById(1), user);
  assert.deepEqual(events, [1]);

  await assert.rejects(
    () => service.register(user),
    /already exists/
  );

  await assert.rejects(
    () => service.getUser(99),
    /not found/
  );
}

async function systemTest() {
  const repository = new UserRepository();
  const service = new UserService(repository);
  const directory = await fs.mkdtemp(
    path.join(os.tmpdir(), 'testing-fundamentals-')
  );

  try {
    await service.register({
      id: 7,
      name: 'System User',
      email: 'system@example.com'
    });

    const file = await service.exportUser(7, directory);
    const content = await fs.readFile(file, 'utf8');
    const exported = JSON.parse(content);

    assert.equal(exported.id, 7);
    assert.equal(exported.name, 'System User');
    assert.equal(exported.email, 'system@example.com');

    await assert.rejects(
      () => service.exportUser(999, directory),
      /not found/
    );
  } finally {
    await fs.rm(directory, { recursive: true, force: true });
  }
}

async function run() {
  const suites = [
    ['UNIT', unitTests],
    ['INTEGRATION', integrationTests],
    ['SYSTEM', systemTest]
  ];

  for (const [name, suite] of suites) {
    const started = performance.now();

    try {
      await suite();
      const duration = (performance.now() - started).toFixed(2);
      console.log(`[PASS] ${name.padEnd(12)} ${duration} ms`);
    } catch (error) {
      console.error(`[FAIL] ${name}`);
      console.error(error);
      process.exitCode = 1;
      return;
    }
  }

  console.log('\nAll testing levels passed.');
}

run().catch(error => {
  console.error('Unexpected test-runner failure:', error);
  process.exitCode = 1;
});
