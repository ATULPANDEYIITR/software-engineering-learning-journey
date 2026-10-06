"use strict";

/*
 * Design Patterns I: Factory, Builder, Singleton
 *
 * This Node.js program models a deployment-notification subsystem.
 *
 * Factory  -> selects the correct notification transport.
 * Builder  -> constructs a complex deployment notification safely.
 * Singleton -> provides one shared audit service for the process.
 *
 * The implementation deliberately keeps these responsibilities separate.
 */

const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");

// ---------------------------------------------------------------------------
// Factory Pattern
// ---------------------------------------------------------------------------

class EmailTransport {
  send(recipient, message) {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipient)) {
      throw new Error("Invalid email recipient.");
    }

    return {
      transport: "email",
      recipient,
      message,
      deliveryId: crypto.randomUUID(),
    };
  }
}

class SmsTransport {
  send(recipient, message) {
    if (!/^\+?[0-9]{8,15}$/.test(recipient)) {
      throw new Error("Invalid SMS recipient.");
    }

    return {
      transport: "sms",
      recipient,
      message,
      deliveryId: crypto.randomUUID(),
    };
  }
}

class PushTransport {
  send(recipient, message) {
    if (!recipient.trim()) {
      throw new Error("Push device token cannot be empty.");
    }

    return {
      transport: "push",
      recipient,
      message,
      deliveryId: crypto.randomUUID(),
    };
  }
}

class NotificationTransportFactory {
  static create(channel) {
    switch (channel) {
      case "email":
        return new EmailTransport();
      case "sms":
        return new SmsTransport();
      case "push":
        return new PushTransport();
      default:
        throw new Error(`Unsupported notification channel: ${channel}`);
    }
  }
}

function demonstrateFactory() {
  console.log("\n=== Factory Pattern ===");

  const requests = [
    ["email", "release@example.com"],
    ["sms", "+919876543210"],
    ["push", "device-token-42"],
  ];

  for (const [channel, recipient] of requests) {
    const transport = NotificationTransportFactory.create(channel);
    console.log(
      transport.send(recipient, `Deployment notification via ${channel}`)
    );
  }
}

// ---------------------------------------------------------------------------
// Builder Pattern
// ---------------------------------------------------------------------------

class DeploymentNotification {
  constructor({
    title,
    body,
    recipient,
    channel,
    priority,
    tags,
    metadata,
    retryCount,
  }) {
    this.title = title;
    this.body = body;
    this.recipient = recipient;
    this.channel = channel;
    this.priority = priority;
    this.tags = Object.freeze([...tags]);
    this.metadata = Object.freeze({ ...metadata });
    this.retryCount = retryCount;

    // Object.freeze prevents accidental mutation of the top-level product.
    Object.freeze(this);
  }
}

class DeploymentNotificationBuilder {
  constructor(title, body, recipient, channel) {
    this.titleValue = title;
    this.bodyValue = body;
    this.recipientValue = recipient;
    this.channelValue = channel;
    this.priorityValue = "normal";
    this.tagsValue = [];
    this.metadataValue = {};
    this.retryCountValue = 3;
  }

  priority(value) {
    const valid = new Set(["low", "normal", "high", "critical"]);
    if (!valid.has(value)) {
      throw new Error(`Invalid priority: ${value}`);
    }

    this.priorityValue = value;
    return this;
  }

  addTag(value) {
    const tag = value.trim();
    if (!tag) {
      throw new Error("A notification tag cannot be empty.");
    }

    if (!this.tagsValue.includes(tag)) {
      this.tagsValue.push(tag);
    }

    return this;
  }

  metadata(key, value) {
    const normalizedKey = key.trim();
    if (!normalizedKey) {
      throw new Error("Metadata key cannot be empty.");
    }

    this.metadataValue[normalizedKey] = String(value);
    return this;
  }

  retryCount(value) {
    if (!Number.isInteger(value) || value < 0 || value > 10) {
      throw new Error("Retry count must be an integer between 0 and 10.");
    }

    this.retryCountValue = value;
    return this;
  }

  validate() {
    if (!this.titleValue.trim()) {
      throw new Error("Notification title is required.");
    }

    if (!this.bodyValue.trim()) {
      throw new Error("Notification body is required.");
    }

    if (!this.recipientValue.trim()) {
      throw new Error("Notification recipient is required.");
    }

    if (!["email", "sms", "push"].includes(this.channelValue)) {
      throw new Error(`Unsupported channel: ${this.channelValue}`);
    }

    if (
      this.channelValue === "email" &&
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.recipientValue)
    ) {
      throw new Error("Email notifications require a valid email address.");
    }

    if (
      this.channelValue === "sms" &&
      !/^\+?[0-9]{8,15}$/.test(this.recipientValue)
    ) {
      throw new Error("SMS notifications require a valid phone number.");
    }
  }

  build() {
    this.validate();

    return new DeploymentNotification({
      title: this.titleValue.trim(),
      body: this.bodyValue.trim(),
      recipient: this.recipientValue.trim(),
      channel: this.channelValue,
      priority: this.priorityValue,
      tags: this.tagsValue,
      metadata: this.metadataValue,
      retryCount: this.retryCountValue,
    });
  }
}

function demonstrateBuilder() {
  console.log("\n=== Builder Pattern ===");

  const notification = new DeploymentNotificationBuilder(
    "Production deployment",
    "Version 4.2.0 has been deployed.",
    "release@example.com",
    "email"
  )
    .priority("high")
    .addTag("deployment")
    .addTag("production")
    .metadata("version", "4.2.0")
    .metadata("service", "release-manager")
    .retryCount(5)
    .build();

  console.log(notification);

  try {
    new DeploymentNotificationBuilder(
      "",
      "Invalid notification",
      "release@example.com",
      "email"
    ).build();
  } catch (error) {
    console.log(`Builder rejected invalid input: ${error.message}`);
  }

  return notification;
}

// ---------------------------------------------------------------------------
// Singleton Pattern
// ---------------------------------------------------------------------------

class AuditLog {
  static instance = null;

  constructor() {
    if (AuditLog.instance) {
      return AuditLog.instance;
    }

    this.events = [];
    AuditLog.instance = this;
  }

  record(type, data = {}) {
    this.events.push({
      timestamp: new Date().toISOString(),
      type,
      data: { ...data },
    });
  }

  snapshot() {
    return this.events.map((event) => ({
      ...event,
      data: { ...event.data },
    }));
  }
}

function demonstrateSingleton() {
  console.log("\n=== Singleton Pattern ===");

  const first = new AuditLog();
  const second = new AuditLog();

  first.record("deployment.started", { version: "4.2.0" });
  second.record("deployment.completed", { version: "4.2.0" });

  console.log("Same object:", first === second);
  console.log("Shared audit events:", first.snapshot());
}

// ---------------------------------------------------------------------------
// Event-driven workflow
// ---------------------------------------------------------------------------

class DeploymentEventBus {
  constructor() {
    this.listeners = new Map();
  }

  on(eventName, listener) {
    if (!this.listeners.has(eventName)) {
      this.listeners.set(eventName, new Set());
    }

    this.listeners.get(eventName).add(listener);

    // Returning an unsubscribe function makes listener lifecycle explicit.
    return () => this.listeners.get(eventName)?.delete(listener);
  }

  emit(eventName, payload) {
    const listeners = this.listeners.get(eventName) || new Set();

    for (const listener of listeners) {
      listener(payload);
    }
  }
}

class DeploymentNotificationService {
  constructor(auditLog = new AuditLog()) {
    this.auditLog = auditLog;
    this.eventBus = new DeploymentEventBus();

    this.eventBus.on("notification.sent", (payload) => {
      this.auditLog.record("notification.sent", payload);
    });

    this.eventBus.on("notification.failed", (payload) => {
      this.auditLog.record("notification.failed", payload);
    });
  }

  async send(notification) {
    this.auditLog.record("notification.requested", {
      channel: notification.channel,
      priority: notification.priority,
    });

    const transport = NotificationTransportFactory.create(
      notification.channel
    );

    try {
      const result = transport.send(
        notification.recipient,
        notification.body
      );

      this.eventBus.emit("notification.sent", {
        channel: notification.channel,
        deliveryId: result.deliveryId,
      });

      return result;
    } catch (error) {
      this.eventBus.emit("notification.failed", {
        channel: notification.channel,
        reason: error.message,
      });
      throw error;
    }
  }
}

// ---------------------------------------------------------------------------
// Configuration boundary
// ---------------------------------------------------------------------------

async function loadNotificationConfiguration(filePath) {
  let content;

  try {
    content = await fs.readFile(filePath, "utf8");
  } catch (error) {
    throw new Error(`Cannot read configuration: ${error.message}`);
  }

  let configuration;

  try {
    configuration = JSON.parse(content);
  } catch {
    throw new Error("Configuration is not valid JSON.");
  }

  const required = ["title", "body", "recipient", "channel"];
  const missing = required.filter(
    (field) => configuration[field] === undefined
  );

  if (missing.length > 0) {
    throw new Error(`Missing fields: ${missing.join(", ")}`);
  }

  const builder = new DeploymentNotificationBuilder(
    String(configuration.title),
    String(configuration.body),
    String(configuration.recipient),
    String(configuration.channel)
  );

  if (configuration.priority !== undefined) {
    builder.priority(String(configuration.priority));
  }

  for (const tag of configuration.tags ?? []) {
    builder.addTag(String(tag));
  }

  for (const [key, value] of Object.entries(
    configuration.metadata ?? {}
  )) {
    builder.metadata(key, value);
  }

  if (configuration.retryCount !== undefined) {
    builder.retryCount(Number(configuration.retryCount));
  }

  return builder.build();
}

async function demonstrateConfigurationBoundary() {
  console.log("\n=== Configuration + Builder ===");

  const temporaryDirectory = await fs.mkdtemp(
    path.join(os.tmpdir(), "patterns-")
  );

  const filePath = path.join(temporaryDirectory, "notification.json");

  const configuration = {
    title: "Security deployment",
    body: "A privileged production deployment was detected.",
    recipient: "+919876543210",
    channel: "sms",
    priority: "critical",
    tags: ["security", "deployment"],
    metadata: {
      service: "release-manager",
      environment: "production",
    },
    retryCount: 4,
  };

  await fs.writeFile(
    filePath,
    JSON.stringify(configuration, null, 2),
    "utf8"
  );

  const notification = await loadNotificationConfiguration(filePath);
  console.log(notification);

  await fs.rm(temporaryDirectory, { recursive: true, force: true });
}

// ---------------------------------------------------------------------------
// Verification
// ---------------------------------------------------------------------------

async function runTests() {
  console.log("\n=== Pattern Verification ===");

  const emailTransport =
    NotificationTransportFactory.create("email");
  const smsTransport =
    NotificationTransportFactory.create("sms");
  const pushTransport =
    NotificationTransportFactory.create("push");

  if (!(emailTransport instanceof EmailTransport)) {
    throw new Error("Factory returned the wrong email product.");
  }

  if (!(smsTransport instanceof SmsTransport)) {
    throw new Error("Factory returned the wrong SMS product.");
  }

  if (!(pushTransport instanceof PushTransport)) {
    throw new Error("Factory returned the wrong push product.");
  }

  const builder = new DeploymentNotificationBuilder(
    "Release",
    "Release completed",
    "team@example.com",
    "email"
  );

  const first = builder.addTag("release").build();
  builder.addTag("second");

  if (first.tags.length !== 1) {
    throw new Error("Built product changed after builder mutation.");
  }

  if (new AuditLog() !== new AuditLog()) {
    throw new Error("Singleton invariant failed.");
  }

  try {
    new DeploymentNotificationBuilder(
      "Invalid",
      "Invalid email",
      "not-an-email",
      "email"
    ).build();

    throw new Error("Invalid email was accepted.");
  } catch (error) {
    if (error.message === "Invalid email was accepted.") {
      throw error;
    }
  }

  const service = new DeploymentNotificationService();
  const result = await service.send(first);

  if (result.transport !== "email") {
    throw new Error("Notification was routed to the wrong transport.");
  }

  console.log("All JavaScript pattern checks passed.");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  demonstrateFactory();
  const notification = demonstrateBuilder();
  demonstrateSingleton();

  console.log("\n=== Combined Workflow ===");

  const service = new DeploymentNotificationService();
  const result = await service.send(notification);
  console.log(result);

  console.log("\nAudit trail:");
  for (const event of service.auditLog.snapshot()) {
    console.log(event);
  }

  await demonstrateConfigurationBoundary();
  await runTests();
}

main().catch((error) => {
  console.error(`Application failed: ${error.message}`);
  process.exitCode = 1;
});
