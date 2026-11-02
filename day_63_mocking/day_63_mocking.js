'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');

const PaymentStatus = Object.freeze({
  APPROVED: 'approved',
  DECLINED: 'declined'
});

class Payment {
  constructor(paymentId, customerId, amount, currency) {
    this.paymentId = paymentId;
    this.customerId = customerId;
    this.amount = amount;
    this.currency = currency;
    Object.freeze(this);
  }
}

class PaymentService extends EventEmitter {
  constructor({ gateway, fraudService, repository }) {
    super();
    this.gateway = gateway;
    this.fraudService = fraudService;
    this.repository = repository;
  }

  validate(payment) {
    if (!(payment instanceof Payment)) {
      throw new TypeError('Expected a Payment object');
    }
    if (!payment.paymentId.trim()) throw new Error('Payment ID is required');
    if (!payment.customerId.trim()) throw new Error('Customer ID is required');
    if (!Number.isFinite(payment.amount) || payment.amount <= 0) {
      throw new Error('Amount must be a positive finite number');
    }
    if (!/^[A-Z]{3}$/.test(payment.currency)) {
      throw new Error('Currency must be a three-letter uppercase code');
    }
  }

  async process(payment) {
    this.validate(payment);

    const suspicious = await this.fraudService.isSuspicious(payment);
    let status;

    if (suspicious) {
      status = PaymentStatus.DECLINED;
    } else {
      status = await this.gateway.authorize(payment);
    }

    await this.repository.save(payment, status);

    this.emit('processed', {
      paymentId: payment.paymentId,
      status
    });

    return status;
  }
}

class StubGateway {
  constructor(status) {
    this.status = status;
    this.calls = [];
  }

  async authorize(payment) {
    this.calls.push(payment.paymentId);
    return this.status;
  }
}

class FakeFraudService {
  constructor(blockedCustomers = new Set()) {
    this.blockedCustomers = new Set(blockedCustomers);
  }

  async isSuspicious(payment) {
    return this.blockedCustomers.has(payment.customerId);
  }
}

class FakeRepository {
  constructor() {
    this.records = new Map();
  }

  async save(payment, status) {
    this.records.set(payment.paymentId, status);
  }
}

class MockGateway {
  constructor(status) {
    this.status = status;
    this.calls = [];
  }

  async authorize(payment) {
    this.calls.push(payment);
    return this.status;
  }

  assertCalledOnceWith(payment) {
    assert.equal(this.calls.length, 1);
    assert.deepEqual(this.calls[0], payment);
  }
}

class MockFraudService {
  constructor(result) {
    this.result = result;
    this.calls = [];
  }

  async isSuspicious(payment) {
    this.calls.push(payment);
    return this.result;
  }
}

async function testStub() {
  const payment = new Payment('P-100', 'C-10', 100, 'USD');
  const gateway = new StubGateway(PaymentStatus.APPROVED);
  const service = new PaymentService({
    gateway,
    fraudService: new FakeFraudService(),
    repository: new FakeRepository()
  });

  const status = await service.process(payment);

  assert.equal(status, PaymentStatus.APPROVED);
  assert.deepEqual(gateway.calls, ['P-100']);
}

async function testFakeBlocksCustomer() {
  const payment = new Payment('P-101', 'C-BLOCKED', 100, 'USD');
  const gateway = new StubGateway(PaymentStatus.APPROVED);
  const repository = new FakeRepository();

  const status = await new PaymentService({
    gateway,
    fraudService: new FakeFraudService(['C-BLOCKED']),
    repository
  }).process(payment);

  assert.equal(status, PaymentStatus.DECLINED);
  assert.equal(gateway.calls.length, 0);
  assert.equal(repository.records.get('P-101'), PaymentStatus.DECLINED);
}

async function testMockInteraction() {
  const payment = new Payment('P-102', 'C-10', 250, 'USD');
  const gateway = new MockGateway(PaymentStatus.APPROVED);
  const fraud = new MockFraudService(false);

  await new PaymentService({
    gateway,
    fraudService: fraud,
    repository: new FakeRepository()
  }).process(payment);

  gateway.assertCalledOnceWith(payment);
  assert.deepEqual(fraud.calls, [payment]);
}

async function testInvalidInput() {
  const gateway = new MockGateway(PaymentStatus.APPROVED);
  const fraud = new MockFraudService(false);

  await assert.rejects(
    () =>
      new PaymentService({
        gateway,
        fraudService: fraud,
        repository: new FakeRepository()
      }).process(new Payment('P-103', 'C-10', -1, 'USD')),
    /positive finite number/
  );

  assert.equal(gateway.calls.length, 0);
  assert.equal(fraud.calls.length, 0);
}

async function testEventDrivenAudit() {
  const payment = new Payment('P-104', 'C-10', 300, 'USD');
  const events = [];

  const service = new PaymentService({
    gateway: new StubGateway(PaymentStatus.APPROVED),
    fraudService: new FakeFraudService(),
    repository: new FakeRepository()
  });

  service.on('processed', event => events.push(event));
  await service.process(payment);

  assert.deepEqual(events, [{
    paymentId: 'P-104',
    status: PaymentStatus.APPROVED
  }]);
}

async function run() {
  await testStub();
  await testFakeBlocksCustomer();
  await testMockInteraction();
  await testInvalidInput();
  await testEventDrivenAudit();

  console.log('All mocking, stubbing, and fake-isolation tests passed.');

  const service = new PaymentService({
    gateway: new StubGateway(PaymentStatus.APPROVED),
    fraudService: new FakeFraudService(),
    repository: new FakeRepository()
  });

  service.on('processed', event => {
    console.log(`event: ${event.paymentId} -> ${event.status}`);
  });

  await service.process(new Payment('P-200', 'C-20', 500, 'USD'));
}

run().catch(error => {
  console.error(`Execution failed: ${error.message}`);
  process.exitCode = 1;
});
