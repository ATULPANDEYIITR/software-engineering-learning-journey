"use strict";

/**
 * Event-driven REST API for task management.
 *
 * Runtime: Node.js 20+
 * Dependencies: Node.js standard library only.
 *
 * Storage is in memory. Replace TaskStore with a durable repository before
 * using multiple processes or deploying a service that must survive restarts.
 */

const http = require("node:http");
const crypto = require("node:crypto");
const { EventEmitter } = require("node:events");

const HOST = process.env.API_HOST || "127.0.0.1";
const PORT = Number.parseInt(process.env.API_PORT || "8080", 10);
const API_TOKEN = process.env.API_TOKEN || "local-development-token";

const MAX_BODY_BYTES = 1_048_576;
const MAX_TITLE_LENGTH = 160;
const MAX_DESCRIPTION_LENGTH = 2_000;
const RATE_LIMIT_MAXIMUM = 120;
const RATE_LIMIT_WINDOW_MS = 60_000;
const IDEMPOTENCY_TTL_MS = 24 * 60 * 60 * 1000;

const TASK_STATUSES = new Set([
    "pending",
    "in_progress",
    "completed",
    "cancelled"
]);

const ALLOWED_TRANSITIONS = new Map([
    ["pending", new Set(["in_progress", "cancelled"])],
    ["in_progress", new Set(["pending", "completed", "cancelled"])],
    ["completed", new Set()],
    ["cancelled", new Set()]
]);

class ApiError extends Error {
    constructor(status, code, message) {
        super(message);
        this.status = status;
        this.code = code;
    }
}

function sha256(value) {
    return crypto.createHash("sha256").update(value, "utf8").digest();
}

function nowIso() {
    return new Date().toISOString();
}

function validateTitle(value) {
    if (typeof value !== "string") {
        throw new ApiError(400, "invalid_title", "Title must be a string.");
    }

    const title = value.trim();
    if (title.length === 0 || title.length > MAX_TITLE_LENGTH) {
        throw new ApiError(
            400,
            "invalid_title",
            `Title must contain between 1 and ${MAX_TITLE_LENGTH} characters.`
        );
    }

    return title;
}

function validateDescription(value) {
    if (value === undefined) {
        return "";
    }

    if (typeof value !== "string" || value.length > MAX_DESCRIPTION_LENGTH) {
        throw new ApiError(
            400,
            "invalid_description",
            `Description must be a string of at most ${MAX_DESCRIPTION_LENGTH} characters.`
        );
    }

    return value;
}

function validateStatus(value) {
    if (typeof value !== "string" || !TASK_STATUSES.has(value)) {
        throw new ApiError(
            400,
            "invalid_status",
            "Status must be pending, in_progress, completed or cancelled."
        );
    }

    return value;
}

function parseIfMatch(value) {
    if (value === undefined) {
        throw new ApiError(
            428,
            "precondition_required",
            "Supply the current task version through If-Match."
        );
    }

    const match = /^"?( [0-9]+ )"?$/.exec(value.replaceAll(" ", ""));
    if (!match || Number(match[1]) < 1 || !Number.isSafeInteger(Number(match[1]))) {
        throw new ApiError(
            400,
            "invalid_if_match",
            "If-Match must contain a positive version number."
        );
    }

    return Number(match[1]);
}

function validateIdempotencyKey(value) {
    if (
        typeof value !== "string" ||
        !/^[A-Za-z0-9._:-]{8,128}$/.test(value)
    ) {
        throw new ApiError(
            400,
            "invalid_idempotency_key",
            "Idempotency-Key must contain 8 to 128 permitted characters."
        );
    }

    return value;
}

class SlidingWindowRateLimiter {
    constructor(maximum, windowMs) {
        this.maximum = maximum;
        this.windowMs = windowMs;
        this.buckets = new Map();
    }

    check(clientAddress) {
        const now = Date.now();
        const cutoff = now - this.windowMs;

        let bucket = this.buckets.get(clientAddress);
        if (!bucket) {
            bucket = [];
            this.buckets.set(clientAddress, bucket);
        }

        while (bucket.length > 0 && bucket[0] <= cutoff) {
            bucket.shift();
        }

        if (bucket.length >= this.maximum) {
            throw new ApiError(
                429,
                "rate_limit_exceeded",
                "Too many requests. Retry after the current rate-limit window."
            );
        }

        bucket.push(now);

        if (this.buckets.size > 10_000) {
            for (const [key, timestamps] of this.buckets.entries()) {
                if (timestamps.length === 0 || timestamps[timestamps.length - 1] <= cutoff) {
                    this.buckets.delete(key);
                }
            }
        }
    }
}

class TaskStore {
    constructor() {
        this.tasks = new Map();
        this.idempotencyRecords = new Map();
        this.nextSequence = 1;
    }

    create(title, description, key) {
        const canonicalPayload = JSON.stringify({
            title,
            description
        });
        const requestHash = sha256(canonicalPayload).toString("hex");
        const now = Date.now();

        // Expired keys can be reused. The operation is synchronous, so the
        // lookup and insertion are atomic relative to other event-loop tasks.
        for (const [storedKey, record] of this.idempotencyRecords.entries()) {
            if (record.expiresAt <= now) {
                this.idempotencyRecords.delete(storedKey);
            }
        }

        const previous = this.idempotencyRecords.get(key);
        if (previous) {
            if (previous.requestHash !== requestHash) {
                throw new ApiError(
                    409,
                    "idempotency_conflict",
                    "This idempotency key was already used with a different request."
                );
            }

            const existingTask = this.tasks.get(previous.taskId);
            if (!existingTask) {
                throw new ApiError(
                    409,
                    "idempotency_record_unavailable",
                    "The original resource is no longer available."
                );
            }

            return {
                task: { ...existingTask },
                replayed: true
            };
        }

        const createdAt = nowIso();
        const id = crypto.randomUUID();

        const task = {
            id,
            title,
            description,
            status: "pending",
            version: 1,
            created_at: createdAt,
            updated_at: createdAt
        };

        this.tasks.set(id, task);
        this.idempotencyRecords.set(key, {
            requestHash,
            taskId: id,
            expiresAt: now + IDEMPOTENCY_TTL_MS
        });

        this.nextSequence += 1;

        return {
            task: { ...task },
            replayed: false
        };
    }

    get(id) {
        const task = this.tasks.get(id);
        return task ? { ...task } : null;
    }

    list({ status, limit, offset }) {
        let items = Array.from(this.tasks.values());

        if (status !== undefined) {
            items = items.filter((task) => task.status === status);
        }

        items.sort((left, right) => {
            const timeDifference =
                Date.parse(right.created_at) - Date.parse(left.created_at);
            return timeDifference || left.id.localeCompare(right.id);
        });

        return items
            .slice(offset, offset + limit)
            .map((task) => ({ ...task }));
    }

    update(id, expectedVersion, changes) {
        const current = this.tasks.get(id);
        if (!current) {
            throw new ApiError(404, "task_not_found", "Task does not exist.");
        }

        if (current.version !== expectedVersion) {
            throw new ApiError(
                412,
                "version_conflict",
                "The task changed. Retrieve its latest representation before updating it."
            );
        }

        const nextStatus = changes.status ?? current.status;
        if (
            nextStatus !== current.status &&
            !ALLOWED_TRANSITIONS.get(current.status).has(nextStatus)
        ) {
            throw new ApiError(
                409,
                "invalid_state_transition",
                `Cannot transition from ${current.status} to ${nextStatus}.`
            );
        }

        const updated = {
            ...current,
            ...changes,
            status: nextStatus,
            version: current.version + 1,
            updated_at: nowIso()
        };

        this.tasks.set(id, updated);
        return { ...updated };
    }

    delete(id, expectedVersion) {
        const current = this.tasks.get(id);
        if (!current) {
            throw new ApiError(404, "task_not_found", "Task does not exist.");
        }

        if (current.version !== expectedVersion) {
            throw new ApiError(
                412,
                "version_conflict",
                "The task changed. Retrieve its latest version before deleting it."
            );
        }

        this.tasks.delete(id);

        for (const [key, record] of this.idempotencyRecords.entries()) {
            if (record.taskId === id) {
                this.idempotencyRecords.delete(key);
            }
        }
    }
}

class AuditEvents extends EventEmitter {
    constructor() {
        super();
        this.on("request", (event) => {
            // Do not record bearer tokens, request bodies or sensitive headers.
            process.stdout.write(
                JSON.stringify({
                    event: "api_request",
                    requestId: event.requestId,
                    method: event.method,
                    route: event.route,
                    status: event.status,
                    durationMs: event.durationMs
                }) + "\n"
            );
        });
    }
}

const store = new TaskStore();
const rateLimiter = new SlidingWindowRateLimiter(
    RATE_LIMIT_MAXIMUM,
    RATE_LIMIT_WINDOW_MS
);
const audit = new AuditEvents();
const expectedTokenDigest = sha256(API_TOKEN);

if (API_TOKEN.length < 16) {
    throw new Error("API_TOKEN must contain at least 16 characters.");
}

if (API_TOKEN === "local-development-token") {
    process.stderr.write(
        "WARNING: Set API_TOKEN to a unique secret before deployment.\n"
    );
}

function authenticate(request) {
    const authorization = request.headers.authorization || "";
    const suppliedToken = authorization.startsWith("Bearer ")
        ? authorization.slice(7)
        : "";

    // Both values are fixed-length SHA-256 digests before the comparison.
    const suppliedDigest = sha256(suppliedToken);
    if (!crypto.timingSafeEqual(suppliedDigest, expectedTokenDigest)) {
        throw new ApiError(
            401,
            "unauthorized",
            "A valid bearer token is required."
        );
    }
}

async function readJson(request) {
    const contentType = (request.headers["content-type"] || "")
        .split(";")[0]
        .trim()
        .toLowerCase();

    if (contentType !== "application/json") {
        throw new ApiError(
            415,
            "unsupported_media_type",
            "Content-Type must be application/json."
        );
    }

    const declaredLength = Number(request.headers["content-length"] || 0);
    if (declaredLength > MAX_BODY_BYTES) {
        throw new ApiError(413, "payload_too_large", "Request body is too large.");
    }

    const chunks = [];
    let totalBytes = 0;

    for await (const chunk of request) {
        totalBytes += chunk.length;
        if (totalBytes > MAX_BODY_BYTES) {
            throw new ApiError(413, "payload_too_large", "Request body is too large.");
        }
        chunks.push(chunk);
    }

    if (totalBytes === 0) {
        throw new ApiError(400, "empty_body", "A JSON request body is required.");
    }

    let parsed;
    try {
        parsed = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    } catch {
        throw new ApiError(
            400,
            "invalid_json",
            "Request body must contain valid JSON."
        );
    }

    if (
        parsed === null ||
        typeof parsed !== "object" ||
        Array.isArray(parsed)
    ) {
        throw new ApiError(
            400,
            "invalid_json_shape",
            "The JSON request body must be an object."
        );
    }

    return parsed;
}

function validateObjectFields(body, allowedFields) {
    const unknown = Object.keys(body).filter(
        (key) => !allowedFields.has(key)
    );

    if (unknown.length > 0) {
        throw new ApiError(
            400,
            "unknown_fields",
            `Unsupported fields: ${unknown.sort().join(", ")}`
        );
    }
}

function parsePagination(searchParams) {
    function parseInteger(name, defaultValue, minimum, maximum) {
        const raw = searchParams.get(name);
        if (raw === null) {
            return defaultValue;
        }

        if (!/^-?\d+$/.test(raw)) {
            throw new ApiError(
                400,
                `invalid_${name}`,
                `${name} must be an integer.`
            );
        }

        const value = Number(raw);
        if (
            !Number.isSafeInteger(value) ||
            value < minimum ||
            value > maximum
        ) {
            throw new ApiError(
                400,
                `invalid_${name}`,
                `${name} must be between ${minimum} and ${maximum}.`
            );
        }

        return value;
    }

    const limit = parseInteger("limit", 20, 1, 100);
    const offset = parseInteger("offset", 0, 0, 1_000_000);

    return { limit, offset };
}

function sendJson(response, status, requestId, payload, extraHeaders = {}) {
    const body = Buffer.from(
        JSON.stringify({
            ...payload,
            request_id: requestId
        }),
        "utf8"
    );

    response.writeHead(status, {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": body.length,
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Request-ID": requestId,
        ...extraHeaders
    });

    response.end(body);
}

function taskResponse(task, requestId, status = 200, extraHeaders = {}) {
    sendJson(
        responseContext.response,
        status,
        requestId,
        { data: task },
        {
            ETag: `"${task.version}"`,
            ...extraHeaders
        }
    );
}

let responseContext = { response: null };

async function routeRequest(request, response, requestId) {
    const url = new URL(request.url, `http://${request.headers.host || "localhost"}`);
    const method = request.method.toUpperCase();
    const path = url.pathname;

    if (path === "/health") {
        if (method !== "GET") {
            throw new ApiError(405, "method_not_allowed", "Use GET.");
        }

        sendJson(response, 200, requestId, { status: "healthy" });
        return 200;
    }

    if (!path.startsWith("/v1/")) {
        throw new ApiError(404, "route_not_found", "Route does not exist.");
    }

    rateLimiter.check(
        request.socket.remoteAddress || "unknown-client"
    );
    authenticate(request);

    if (path === "/v1/tasks") {
        if (method === "GET") {
            const status = url.searchParams.get("status") || undefined;
            if (status !== undefined) {
                validateStatus(status);
            }

            const pagination = parsePagination(url.searchParams);
            const items = store.list({
                status,
                ...pagination
            });

            sendJson(response, 200, requestId, {
                data: items,
                pagination: {
                    ...pagination,
                    returned: items.length
                }
            });
            return 200;
        }

        if (method === "POST") {
            const body = await readJson(request);
            validateObjectFields(body, new Set(["title", "description"]));

            const title = validateTitle(body.title);
            const description = validateDescription(body.description);
            const key = validateIdempotencyKey(
                request.headers["idempotency-key"]
            );

            const result = store.create(title, description, key);
            const headers = {
                ETag: `"${result.task.version}"`
            };

            if (result.replayed) {
                headers["Idempotent-Replayed"] = "true";
            }

            sendJson(
                response,
                result.replayed ? 200 : 201,
                requestId,
                { data: result.task },
                headers
            );
            return result.replayed ? 200 : 201;
        }

        throw new ApiError(
            405,
            "method_not_allowed",
            "Supported methods are GET and POST."
        );
    }

    const itemMatch = /^\/v1\/tasks\/([0-9a-f-]{36})$/i.exec(path);
    if (!itemMatch) {
        throw new ApiError(404, "route_not_found", "Route does not exist.");
    }

    const taskId = itemMatch[1];

    if (method === "GET") {
        const task = store.get(taskId);
        if (!task) {
            throw new ApiError(404, "task_not_found", "Task does not exist.");
        }

        sendJson(
            response,
            200,
            requestId,
            { data: task },
            { ETag: `"${task.version}"` }
        );
        return 200;
    }

    if (method === "PATCH") {
        const expectedVersion = parseIfMatch(request.headers["if-match"]);
        const body = await readJson(request);

        validateObjectFields(
            body,
            new Set(["title", "description", "status"])
        );

        if (Object.keys(body).length === 0) {
            throw new ApiError(
                400,
                "empty_patch",
                "At least one field must be supplied."
            );
        }

        const changes = {};
        if (Object.hasOwn(body, "title")) {
            changes.title = validateTitle(body.title);
        }
        if (Object.hasOwn(body, "description")) {
            changes.description = validateDescription(body.description);
        }
        if (Object.hasOwn(body, "status")) {
            changes.status = validateStatus(body.status);
        }

        const task = store.update(taskId, expectedVersion, changes);
        sendJson(
            response,
            200,
            requestId,
            { data: task },
            { ETag: `"${task.version}"` }
        );
        return 200;
    }

    if (method === "DELETE") {
        const expectedVersion = parseIfMatch(request.headers["if-match"]);
        store.delete(taskId, expectedVersion);

        sendJson(response, 200, requestId, {
            data: {
                id: taskId,
                deleted: true
            }
        });
        return 200;
    }

    throw new ApiError(
        405,
        "method_not_allowed",
        "Supported methods are GET, PATCH and DELETE."
    );
}

const server = http.createServer(async (request, response) => {
    const requestId = crypto.randomUUID();
    const started = performance.now();
    let status = 500;

    responseContext = { response };

    try {
        status = await routeRequest(request, response, requestId);
    } catch (error) {
        if (error instanceof ApiError) {
            status = error.status;
            sendJson(response, error.status, requestId, {
                error: {
                    code: error.code,
                    message: error.message
                }
            });
        } else {
            status = 500;
            process.stderr.write(
                JSON.stringify({
                    level: "error",
                    requestId,
                    message: error.message
                }) + "\n"
            );

            if (!response.headersSent) {
                sendJson(response, 500, requestId, {
                    error: {
                        code: "internal_server_error",
                        message: "An unexpected server error occurred."
                    }
                });
            } else {
                response.destroy();
            }
        }
    } finally {
        audit.emit("request", {
            requestId,
            method: request.method,
            route: new URL(
                request.url,
                `http://${request.headers.host || "localhost"}`
            ).pathname,
            status,
            durationMs: Number((performance.now() - started).toFixed(2))
        });
    }
});

server.on("clientError", (_error, socket) => {
    if (socket.writable) {
        socket.end(
            "HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n"
        );
    }
});

server.listen(PORT, HOST, () => {
    process.stdout.write(
        `Task API listening on http://${HOST}:${PORT}\n`
    );
});

function shutdown(signal) {
    process.stdout.write(`${signal} received; closing server.\n`);

    server.close((error) => {
        if (error) {
            process.stderr.write(`${error.message}\n`);
            process.exitCode = 1;
        }
    });

    setTimeout(() => {
        server.closeAllConnections();
    }, 5_000).unref();
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
