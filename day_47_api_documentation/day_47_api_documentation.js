"use strict";

/*
 * API Documentation and Contract Processing
 *
 * Demonstrates OpenAPI operations as executable JavaScript objects, route
 * matching, event-driven contract enforcement, consumer expectations, HTTP
 * response conformance, and API specification evolution.
 *
 * Runtime: Node.js 18 or later. No external packages are required.
 */

const assert = require("node:assert/strict");
const { writeFile } = require("node:fs/promises");

const contract = Object.freeze({
  openapi: "3.1.0",
  info: Object.freeze({
    title: "Equipment Registry API",
    version: "2.4.0",
  }),
  servers: Object.freeze([
    Object.freeze({ url: "https://registry.example.test/api/v2" }),
  ]),
  components: Object.freeze({
    securitySchemes: Object.freeze({
      BearerAuth: Object.freeze({
        type: "http",
        scheme: "bearer",
      }),
    }),
    schemas: Object.freeze({
      Equipment: Object.freeze({
        type: "object",
        required: ["id", "serialNumber", "condition"],
        properties: Object.freeze({
          id: Object.freeze({ type: "integer", minimum: 1 }),
          serialNumber: Object.freeze({
            type: "string",
            minLength: 6,
            maxLength: 32,
          }),
          condition: Object.freeze({
            type: "string",
            enum: ["operational", "maintenance", "retired"],
          }),
          location: Object.freeze({ type: "string" }),
        }),
        additionalProperties: false,
      }),
      RegisterEquipment: Object.freeze({
        type: "object",
        required: ["serialNumber", "condition"],
        properties: Object.freeze({
          serialNumber: Object.freeze({
            type: "string",
            minLength: 6,
            maxLength: 32,
          }),
          condition: Object.freeze({
            type: "string",
            enum: ["operational", "maintenance", "retired"],
          }),
          location: Object.freeze({ type: "string" }),
        }),
        additionalProperties: false,
      }),
    }),
  }),
});

const operations = [
  {
    operationId: "searchEquipment",
    method: "GET",
    path: "/equipment",
    responses: [200, 401],
    authRequired: true,
  },
  {
    operationId: "registerEquipment",
    method: "POST",
    path: "/equipment",
    requestSchema: "RegisterEquipment",
    responses: [201, 400, 401, 409],
    authRequired: true,
  },
  {
    operationId: "getEquipment",
    method: "GET",
    path: "/equipment/{equipmentId}",
    responses: [200, 400, 401, 404],
    authRequired: true,
  },
  {
    operationId: "retireEquipment",
    method: "PATCH",
    path: "/equipment/{equipmentId}",
    requestSchema: "EquipmentPatch",
    responses: [200, 400, 401, 404],
    authRequired: true,
  },
];

class ContractViolation extends Error {
  constructor(path, message) {
    super(`${path}: ${message}`);
    this.name = "ContractViolation";
    this.path = path;
  }
}

class HttpProblem extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }

  toResponse() {
    return {
      status: this.status,
      headers: { "content-type": "application/json" },
      body: {
        error: {
          code: this.code,
          message: this.message,
        },
      },
    };
  }
}

function isPlainObject(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

/*
 * Validate a focused JSON Schema subset. A production implementation should
 * use a standards-compliant JSON Schema validator for arbitrary OpenAPI schemas.
 */
function validateValue(value, schema, path = "$") {
  const issues = [];
  const type = schema.type;

  const matchesType = {
    object: isPlainObject,
    array: Array.isArray,
    string: (v) => typeof v === "string",
    integer: (v) => Number.isSafeInteger(v),
    number: (v) => typeof v === "number" && Number.isFinite(v),
    boolean: (v) => typeof v === "boolean",
    null: (v) => v === null,
  };

  if (type && matchesType[type] && !matchesType[type](value)) {
    return [`${path}: expected ${type}`];
  }

  if (schema.enum && !schema.enum.includes(value)) {
    issues.push(`${path}: expected one of ${schema.enum.join(", ")}`);
  }

  if (typeof value === "string") {
    if (schema.minLength !== undefined && value.length < schema.minLength) {
      issues.push(`${path}: shorter than ${schema.minLength} characters`);
    }
    if (schema.maxLength !== undefined && value.length > schema.maxLength) {
      issues.push(`${path}: longer than ${schema.maxLength} characters`);
    }
    if (schema.pattern && !new RegExp(schema.pattern).test(value)) {
      issues.push(`${path}: pattern mismatch`);
    }
  }

  if (typeof value === "number" && Number.isFinite(value)) {
    if (schema.minimum !== undefined && value < schema.minimum) {
      issues.push(`${path}: below minimum ${schema.minimum}`);
    }
    if (schema.maximum !== undefined && value > schema.maximum) {
      issues.push(`${path}: above maximum ${schema.maximum}`);
    }
  }

  if (isPlainObject(value)) {
    for (const requiredName of schema.required || []) {
      if (!Object.hasOwn(value, requiredName)) {
        issues.push(`${path}.${requiredName}: required property missing`);
      }
    }

    const properties = schema.properties || {};
    for (const [name, child] of Object.entries(value)) {
      if (!Object.hasOwn(properties, name)) {
        if (schema.additionalProperties === false) {
          issues.push(`${path}.${name}: unknown property`);
        }
        continue;
      }
      issues.push(...validateValue(child, properties[name], `${path}.${name}`));
    }
  }

  if (Array.isArray(value) && schema.items) {
    value.forEach((item, index) => {
      issues.push(...validateValue(item, schema.items, `${path}[${index}]`));
    });
  }

  return issues;
}

function matchRoute(template, pathname) {
  const expected = template.split("/").filter(Boolean);
  const actual = pathname.split("/").filter(Boolean);

  if (expected.length !== actual.length) {
    return null;
  }

  const params = Object.create(null);

  for (let index = 0; index < expected.length; index += 1) {
    const segment = expected[index];
    const actualSegment = actual[index];

    if (segment.startsWith("{") && segment.endsWith("}")) {
      const parameterName = segment.slice(1, -1);
      try {
        params[parameterName] = decodeURIComponent(actualSegment);
      } catch {
        throw new HttpProblem(400, "INVALID_PATH_ENCODING", "Malformed path encoding");
      }
    } else if (segment !== actualSegment) {
      return null;
    }
  }

  return params;
}

function findOperation(method, pathname) {
  const matches = [];

  for (const operation of operations) {
    if (operation.method !== method.toUpperCase()) {
      continue;
    }

    const params = matchRoute(operation.path, pathname);
    if (params !== null) {
      matches.push({ operation, params });
    }
  }

  if (matches.length > 1) {
    throw new Error(`Ambiguous route configuration for ${method} ${pathname}`);
  }

  return matches[0] || null;
}

function assertDocumentConsistency(document, registry) {
  const errors = [];

  if (document.openapi !== "3.1.0") {
    errors.push("Expected OpenAPI 3.1.0");
  }

  const ids = new Set();
  for (const operation of registry) {
    if (ids.has(operation.operationId)) {
      errors.push(`Duplicate operationId: ${operation.operationId}`);
    }
    ids.add(operation.operationId);

    if (!operation.path.startsWith("/")) {
      errors.push(`${operation.operationId}: path must start with /`);
    }

    if (!operation.responses.length) {
      errors.push(`${operation.operationId}: no responses documented`);
    }
  }

  return errors;
}

function serializeQuery(parameters) {
  const query = new URLSearchParams();

  for (const [name, value] of Object.entries(parameters)) {
    if (value === undefined || value === null) {
      continue;
    }

    if (Array.isArray(value)) {
      for (const item of value) {
        query.append(name, String(item));
      }
    } else {
      query.set(name, String(value));
    }
  }

  return query.toString();
}

class EquipmentService {
  #records = new Map();
  #nextId = 1;
  #listeners = new Map();

  constructor() {
    this.on("equipment.registered", (event) => {
      console.log(`Audit event: equipment ${event.equipment.id} registered`);
    });
  }

  on(eventName, listener) {
    if (typeof listener !== "function") {
      throw new TypeError("Event listener must be a function");
    }
    const listeners = this.#listeners.get(eventName) || new Set();
    listeners.add(listener);
    this.#listeners.set(eventName, listeners);

    // Returning an unsubscribe function prevents long-lived subscribers from
    // accumulating accidentally in a persistent server process.
    return () => {
      listeners.delete(listener);
    };
  }

  emit(eventName, payload) {
    for (const listener of this.#listeners.get(eventName) || []) {
      listener(payload);
    }
  }

  #authenticate(authorization) {
    if (authorization !== "Bearer equipment-demo-token") {
      throw new HttpProblem(401, "UNAUTHENTICATED", "Bearer token is missing or invalid");
    }
  }

  #snapshot(record) {
    // Never expose the mutable object held inside the service's private Map.
    return Object.freeze({ ...record });
  }

  async handle({ method, url, headers = {}, body }) {
    try {
      this.#authenticate(headers.authorization);

      const parsedUrl = new URL(url, "https://registry.example.test");
      const route = findOperation(method, parsedUrl.pathname);

      if (!route) {
        throw new HttpProblem(404, "ROUTE_NOT_FOUND", "No matching API operation");
      }

      const { operation, params } = route;

      if (operation.operationId === "searchEquipment") {
        const values = [...this.#records.values()];
        return {
          status: 200,
          headers: { "content-type": "application/json" },
          body: { items: values.map((record) => this.#snapshot(record)) },
        };
      }

      if (operation.operationId === "registerEquipment") {
        const schema = contract.components.schemas.RegisterEquipment;
        const issues = validateValue(body, schema);

        if (issues.length) {
          throw new HttpProblem(400, "INVALID_BODY", issues.join("; "));
        }

        const duplicate = [...this.#records.values()].some(
          (record) => record.serialNumber === body.serialNumber,
        );

        if (duplicate) {
          throw new HttpProblem(409, "DUPLICATE_SERIAL", "Serial number already exists");
        }

        const equipment = {
          id: this.#nextId,
          serialNumber: body.serialNumber,
          condition: body.condition,
          ...(body.location === undefined ? {} : { location: body.location }),
        };

        this.#nextId += 1;
        this.#records.set(equipment.id, equipment);
        this.emit("equipment.registered", { equipment: this.#snapshot(equipment) });

        return {
          status: 201,
          headers: {
            "content-type": "application/json",
            location: `/equipment/${equipment.id}`,
          },
          body: this.#snapshot(equipment),
        };
      }

      if (operation.operationId === "getEquipment") {
        const id = Number(params.equipmentId);

        if (!Number.isSafeInteger(id) || id < 1) {
          throw new HttpProblem(400, "INVALID_ID", "equipmentId must be positive");
        }

        const equipment = this.#records.get(id);
        if (!equipment) {
          throw new HttpProblem(404, "NOT_FOUND", "Equipment does not exist");
        }

        return {
          status: 200,
          headers: { "content-type": "application/json" },
          body: this.#snapshot(equipment),
        };
      }

      if (operation.operationId === "retireEquipment") {
        const id = Number(params.equipmentId);
        const equipment = this.#records.get(id);

        if (!Number.isSafeInteger(id) || id < 1 || !equipment) {
          throw new HttpProblem(404, "NOT_FOUND", "Equipment does not exist");
        }

        if (!isPlainObject(body) || Object.keys(body).length === 0) {
          throw new HttpProblem(400, "INVALID_BODY", "A non-empty JSON object is required");
        }

        const allowed = new Set(["condition", "location"]);
        const unknown = Object.keys(body).filter((key) => !allowed.has(key));
        if (unknown.length) {
          throw new HttpProblem(400, "INVALID_BODY", `Unknown properties: ${unknown.join(", ")}`);
        }

        if (
          body.condition !== undefined &&
          !["operational", "maintenance", "retired"].includes(body.condition)
        ) {
          throw new HttpProblem(400, "INVALID_BODY", "Invalid equipment condition");
        }

        if (equipment.condition === "retired" && body.condition !== "retired") {
          throw new HttpProblem(
            409,
            "INVALID_TRANSITION",
            "Retired equipment cannot return to operational status",
          );
        }

        Object.assign(equipment, body);
        return {
          status: 200,
          headers: { "content-type": "application/json" },
          body: this.#snapshot(equipment),
        };
      }

      throw new HttpProblem(501, "UNIMPLEMENTED", "Operation is not implemented");
    } catch (error) {
      if (error instanceof HttpProblem) {
        return error.toResponse();
      }
      throw error;
    }
  }
}

function compareResponseSchemas(previous, current, path = "$") {
  const changes = [];

  if (previous.type !== current.type) {
    return [`${path}: response type changed`];
  }

  const previousRequired = new Set(previous.required || []);
  const currentRequired = new Set(current.required || []);

  for (const key of currentRequired) {
    if (!previousRequired.has(key)) {
      changes.push(`${path}.${key}: newly required property`);
    }
  }

  const oldProperties = previous.properties || {};
  const newProperties = current.properties || {};

  for (const key of Object.keys(oldProperties)) {
    if (!Object.hasOwn(newProperties, key)) {
      changes.push(`${path}.${key}: removed response property`);
    } else {
      changes.push(
        ...compareResponseSchemas(oldProperties[key], newProperties[key], `${path}.${key}`),
      );
    }
  }

  if (previous.enum && current.enum) {
    const removed = previous.enum.filter((value) => !current.enum.includes(value));
    if (removed.length) {
      changes.push(`${path}: removed enum values ${removed.join(", ")}`);
    }
  }

  return changes;
}

async function runContractTests() {
  assert.deepEqual(assertDocumentConsistency(contract, operations), []);

  assert.equal(
    serializeQuery({ status: ["operational", "maintenance"], offset: 10 }),
    "status=operational&status=maintenance&offset=10",
  );

  assert.deepEqual(matchRoute("/equipment/{equipmentId}", "/equipment/42"), {
    equipmentId: "42",
  });
  assert.equal(matchRoute("/equipment/{equipmentId}", "/equipment"), null);

  const service = new EquipmentService();
  const authorization = { authorization: "Bearer equipment-demo-token" };

  const created = await service.handle({
    method: "POST",
    url: "/equipment",
    headers: authorization,
    body: {
      serialNumber: "EQ-2026-0042",
      condition: "operational",
      location: "Lucknow Operations Centre",
    },
  });

  assert.equal(created.status, 201);
  assert.equal(created.body.id, 1);

  const duplicate = await service.handle({
    method: "POST",
    url: "/equipment",
    headers: authorization,
    body: {
      serialNumber: "EQ-2026-0042",
      condition: "operational",
    },
  });
  assert.equal(duplicate.status, 409);

  const invalid = await service.handle({
    method: "POST",
    url: "/equipment",
    headers: authorization,
    body: { serialNumber: "X", condition: "broken" },
  });
  assert.equal(invalid.status, 400);

  const unauthorized = await service.handle({
    method: "GET",
    url: "/equipment",
  });
  assert.equal(unauthorized.status, 401);

  const retired = await service.handle({
    method: "PATCH",
    url: "/equipment/1",
    headers: authorization,
    body: { condition: "retired" },
  });
  assert.equal(retired.status, 200);

  const invalidTransition = await service.handle({
    method: "PATCH",
    url: "/equipment/1",
    headers: authorization,
    body: { condition: "operational" },
  });
  assert.equal(invalidTransition.status, 409);

  const previousSchema = {
    type: "object",
    required: ["id"],
    properties: {
      id: { type: "integer" },
      label: { type: "string" },
    },
  };
  const currentSchema = {
    type: "object",
    required: ["id", "condition"],
    properties: {
      id: { type: "integer" },
      condition: { type: "string" },
    },
  };

  const changes = compareResponseSchemas(previousSchema, currentSchema);
  assert(changes.some((change) => change.includes("newly required property")));
  assert(changes.some((change) => change.includes("removed response property")));

  console.log("All JavaScript contract tests passed.");
  console.log(`Schema evolution findings: ${changes.join(" | ")}`);
  console.log("Contract checks: PASS");
}

function buildOpenApiArtifact() {
  const paths = {};

  for (const operation of operations) {
    const pathItem = paths[operation.path] || {};
    const responses = {};

    for (const status of operation.responses) {
      responses[String(status)] = {
        description: `Documented HTTP ${status} response`,
      };
    }

    pathItem[operation.method.toLowerCase()] = {
      operationId: operation.operationId,
      summary: operation.operationId,
      responses,
      ...(operation.authRequired ? { security: [{ BearerAuth: [] }] } : {}),
    };

    paths[operation.path] = pathItem;
  }

  return {
    openapi: contract.openapi,
    info: contract.info,
    servers: contract.servers,
    paths,
    components: contract.components,
  };
}

async function main() {
  await runContractTests();

  const artifact = buildOpenApiArtifact();
  const json = JSON.stringify(artifact, null, 2);
  assert.equal(JSON.parse(json).openapi, "3.1.0");

  if (process.argv.includes("--export")) {
    // Export is explicit; callers should choose a controlled build directory
    // when integrating this code into a repository pipeline.
    await writeFile("openapi-equipment.json", `${json}\n`, "utf8");
    console.log("Exported openapi-equipment.json");
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
