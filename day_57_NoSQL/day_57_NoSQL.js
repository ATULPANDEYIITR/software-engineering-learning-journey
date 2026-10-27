"use strict";

/*
 * NoSQL model case study.
 * The four models are deliberately represented differently:
 * document data uses nested objects, key-value data uses Map,
 * wide-column data uses sparse row maps, and graph data uses adjacency lists.
 */

class ValidationError extends Error {}
class NotFoundError extends Error {}

class DocumentStore {
  constructor() {
    this.documents = new Map();
    this.indexes = new Map();
  }

  validateId(id) {
    if (typeof id !== "string" || id.length === 0 || id.length > 256) {
      throw new ValidationError("Document ID must contain 1-256 characters.");
    }
  }

  insert(id, document) {
    this.validateId(id);
    if (!document || typeof document !== "object" || Array.isArray(document)) {
      throw new ValidationError("A document must be an object.");
    }
    if (this.documents.has(id)) {
      throw new ValidationError(`Document ${id} already exists.`);
    }

    const stored = structuredClone(document);
    this.documents.set(id, {
      id,
      data: stored,
      version: 1,
      updatedAt: Date.now()
    });
    this.indexDocument(id, stored);
  }

  indexDocument(id, document) {
    for (const [field, value] of Object.entries(document)) {
      if (
        value === null ||
        typeof value === "string" ||
        typeof value === "number" ||
        typeof value === "boolean"
      ) {
        if (!this.indexes.has(field)) {
          this.indexes.set(field, new Map());
        }
        const fieldIndex = this.indexes.get(field);
        const normalized = JSON.stringify(value);
        if (!fieldIndex.has(normalized)) {
          fieldIndex.set(normalized, new Set());
        }
        fieldIndex.get(normalized).add(id);
      }
    }
  }

  removeFromIndexes(id) {
    for (const fieldIndex of this.indexes.values()) {
      for (const ids of fieldIndex.values()) {
        ids.delete(id);
      }
    }
  }

  update(id, changes) {
    const document = this.get(id);
    if (!changes || typeof changes !== "object" || Array.isArray(changes)) {
      throw new ValidationError("Updates must be an object.");
    }

    this.removeFromIndexes(id);
    Object.assign(document.data, structuredClone(changes));
    document.version += 1;
    document.updatedAt = Date.now();
    this.indexDocument(id, document.data);
  }

  get(id) {
    const document = this.documents.get(id);
    if (!document) {
      throw new NotFoundError(`Document ${id} does not exist.`);
    }
    return structuredClone(document);
  }

  find(field, value) {
    const fieldIndex = this.indexes.get(field);
    if (!fieldIndex) return [];

    const ids = fieldIndex.get(JSON.stringify(value)) ?? new Set();
    return [...ids].sort().map(id => this.get(id));
  }
}

class KeyValueStore {
  constructor() {
    this.values = new Map();
  }

  validateKey(key) {
    if (typeof key !== "string" || key.length < 1 || key.length > 256) {
      throw new ValidationError("Key must contain 1-256 characters.");
    }
  }

  purge(key) {
    const entry = this.values.get(key);
    if (!entry) return;

    if (entry.expiresAt !== null && Date.now() >= entry.expiresAt) {
      this.values.delete(key);
    }
  }

  set(key, value, ttlMs = null) {
    this.validateKey(key);
    if (ttlMs !== null && (!Number.isFinite(ttlMs) || ttlMs <= 0)) {
      throw new ValidationError("TTL must be a positive finite number.");
    }

    this.values.set(key, {
      value: structuredClone(value),
      expiresAt: ttlMs === null ? null : Date.now() + ttlMs
    });
  }

  get(key, fallback = null) {
    this.validateKey(key);
    this.purge(key);
    const entry = this.values.get(key);
    return entry ? structuredClone(entry.value) : fallback;
  }

  compareAndSet(key, expected, replacement) {
    const current = this.get(key, undefined);
    if (!Object.is(current, expected)) return false;
    this.set(key, replacement);
    return true;
  }

  delete(key) {
    this.validateKey(key);
    this.purge(key);
    return this.values.delete(key);
  }
}

class ColumnFamilyStore {
  constructor() {
    this.rows = new Map();
  }

  put(rowKey, columns) {
    if (typeof rowKey !== "string" || rowKey.length === 0) {
      throw new ValidationError("Row key cannot be empty.");
    }
    if (!columns || typeof columns !== "object" || Array.isArray(columns)) {
      throw new ValidationError("Columns must be an object.");
    }

    const row = this.rows.get(rowKey) ?? new Map();
    for (const [column, value] of Object.entries(columns)) {
      row.set(column, structuredClone(value));
    }
    this.rows.set(rowKey, row);
  }

  get(rowKey, selectedColumns = null) {
    const row = this.rows.get(rowKey);
    if (!row) throw new NotFoundError(`Row ${rowKey} does not exist.`);

    const result = {};
    const columns = selectedColumns ?? [...row.keys()];
    for (const column of columns) {
      if (row.has(column)) {
        result[column] = structuredClone(row.get(column));
      }
    }
    return result;
  }

  query(column, expectedValue) {
    const result = [];
    for (const [rowKey, row] of this.rows) {
      if (Object.is(row.get(column), expectedValue)) {
        result.push({ rowKey, columns: this.get(rowKey) });
      }
    }
    return result;
  }
}

class GraphStore {
  constructor() {
    this.nodes = new Map();
    this.adjacency = new Map();
  }

  addNode(id, labels, properties = {}) {
    if (!id || this.nodes.has(id)) {
      throw new ValidationError("Node IDs must be unique and non-empty.");
    }
    this.nodes.set(id, {
      id,
      labels: new Set(labels),
      properties: structuredClone(properties)
    });
    this.adjacency.set(id, []);
  }

  addEdge(source, target, relationship, properties = {}) {
    if (!this.nodes.has(source) || !this.nodes.has(target)) {
      throw new NotFoundError("Both graph endpoints must exist.");
    }
    if (!relationship) {
      throw new ValidationError("Relationship cannot be empty.");
    }

    this.adjacency.get(source).push({
      source,
      target,
      relationship,
      properties: structuredClone(properties)
    });
  }

  neighbors(id, relationship = null) {
    if (!this.nodes.has(id)) throw new NotFoundError(id);

    return this.adjacency
      .get(id)
      .filter(edge => relationship === null || edge.relationship === relationship)
      .map(edge => structuredClone(this.nodes.get(edge.target)));
  }

  shortestPath(start, target) {
    if (!this.nodes.has(start) || !this.nodes.has(target)) {
      throw new NotFoundError("Both graph nodes must exist.");
    }

    const queue = [start];
    const previous = new Map([[start, null]]);

    for (let index = 0; index < queue.length; index++) {
      const current = queue[index];

      if (current === target) {
        const path = [];
        let node = current;
        while (node !== null) {
          path.push(node);
          node = previous.get(node);
        }
        return path.reverse();
      }

      for (const edge of this.adjacency.get(current)) {
        if (!previous.has(edge.target)) {
          previous.set(edge.target, current);
          queue.push(edge.target);
        }
      }
    }

    return null;
  }
}

async function processEvents(events, handler, concurrency = 2) {
  if (!Number.isInteger(concurrency) || concurrency < 1) {
    throw new ValidationError("Concurrency must be a positive integer.");
  }

  const results = [];
  let cursor = 0;

  async function worker() {
    while (cursor < events.length) {
      const index = cursor++;
      try {
        results[index] = await handler(events[index]);
      } catch (error) {
        results[index] = {
          ok: false,
          error: error.message
        };
      }
    }
  }

  await Promise.all(
    Array.from(
      { length: Math.min(concurrency, events.length) },
      () => worker()
    )
  );

  return results;
}

async function main() {
  const documents = new DocumentStore();
  documents.insert("u100", {
    name: "Atul",
    department: "R&D",
    security: { clearance: "internal" },
    active: true
  });
  documents.insert("u101", {
    name: "Maya",
    department: "R&D",
    skills: ["Java", "Graph"]
  });
  documents.update("u100", { region: "Lucknow" });

  const sessions = new KeyValueStore();
  sessions.set("session:u100", { authenticated: true }, 30_000);

  const telemetry = new ColumnFamilyStore();
  telemetry.put("device:01", {
    region: "Lucknow",
    temperature: 31.5,
    signal: 94
  });
  telemetry.put("device:02", {
    region: "Delhi",
    signal: 87
  });

  const graph = new GraphStore();
  graph.addNode("team", ["Team"], { name: "R&D" });
  graph.addNode("repo", ["Repository"], { name: "security-platform" });
  graph.addNode("service", ["Service"], { name: "telemetry" });
  graph.addNode("db", ["Database"], { name: "events" });
  graph.addEdge("team", "repo", "OWNS");
  graph.addEdge("repo", "service", "CONTAINS");
  graph.addEdge("service", "db", "USES");

  const events = [
    { key: "cache:1", value: "document" },
    { key: "cache:2", value: "column" },
    { key: "", value: "invalid" }
  ];

  const processed = await processEvents(events, async event => {
    if (!event.key) throw new ValidationError("Event key is required.");
    return { ok: true, key: event.key, model: event.value };
  });

  console.log("DOCUMENT");
  console.log(documents.find("department", "R&D"));

  console.log("\nKEY-VALUE");
  console.log(sessions.get("session:u100"));

  console.log("\nCOLUMN-FAMILY");
  console.log(telemetry.query("signal", 94));

  console.log("\nGRAPH");
  console.log(graph.shortestPath("team", "db"));

  console.log("\nASYNC EVENT PROCESSING");
  console.log(processed);

  console.log("\nMODEL SELECTION");
  console.log({
    document: "Flexible aggregate-oriented records",
    keyValue: "Fast direct lookup and state storage",
    columnFamily: "Sparse high-volume rows",
    graph: "Relationship-centric traversal"
  });
}

main().catch(error => {
  console.error("Fatal error:", error.message);
  process.exitCode = 1;
});
