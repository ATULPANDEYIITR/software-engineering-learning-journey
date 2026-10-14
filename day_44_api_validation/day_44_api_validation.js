"use strict";

/*
 * API Validation and Error Responses
 *
 * Node.js standard-library implementation focused on request normalization,
 * schema validation, asynchronous request processing, structured errors,
 * and safe HTTP response serialization.
 *
 * Run:
 *   node api-validation.js
 */

const { randomUUID } = require("node:crypto");
const http = require("node:http");

class ApiError extends Error {
    constructor(status, code, message, details = []) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.code = code;
        this.details = details;
    }
}

function validationIssue(field, code, message) {
    return { field, code, message };
}

function validateObject(value, field = "body") {
    if (
        value === null ||
        typeof value !== "object" ||
        Array.isArray(value)
    ) {
        throw new ApiError(
            422,
            "validation_failed",
            "The request body must be a JSON object.",
            [validationIssue(field, "invalid_type", "Expected a JSON object.")]
        );
    }
    return value;
}

function validateString(value, field, { min = 1, max = 255 } = {}) {
    if (typeof value !== "string") {
        throw new ApiError(
            422,
            "validation_failed",
            "One or more fields failed validation.",
            [validationIssue(field, "invalid_type", "Expected a string.")]
        );
    }

    const normalized = value.trim();

    if (normalized.length < min || normalized.length > max) {
        throw new ApiError(
            422,
            "validation_failed",
            "One or more fields failed validation.",
            [
                validationIssue(
                    field,
                    "invalid_length",
                    `Length must be between ${min} and ${max} characters.`
                )
            ]
        );
    }

    return normalized;
}

function validateEmail(value) {
    const email = validateString(value, "email", { min: 3, max: 254 });

    // This is a basic application check, not proof that a mailbox exists.
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        throw new ApiError(
            422,
            "validation_failed",
            "One or more fields failed validation.",
            [
                validationIssue(
                    "email",
                    "invalid_email",
                    "Enter a valid email address."
                )
            ]
        );
    }

    return email;
}

function validateAge(value) {
    // Number.isInteger alone is insufficient because NaN and Infinity need
    // careful handling in general numeric APIs; it rejects both here.
    if (!Number.isInteger(value) || typeof value !== "number") {
        throw new ApiError(
            422,
            "validation_failed",
            "One or more fields failed validation.",
            [validationIssue("age", "invalid_type", "Expected an integer.")]
        );
    }

    if (value < 18 || value > 120) {
        throw new ApiError(
            422,
            "validation_failed",
            "One or more fields failed validation.",
            [
                validationIssue(
                    "age",
                    "out_of_range",
                    "Age must be between 18 and 120."
                )
            ]
        );
    }

    return value;
}

function validateCreateUser(payload) {
    validateObject(payload);

    const allowed = new Set(["name", "email", "age"]);
    const details = [];

    for (const key of Object.keys(payload)) {
        if (!allowed.has(key)) {
            details.push(
                validationIssue(
                    key,
                    "unknown_field",
                    "This field is not accepted."
                )
            );
        }
    }

    const validated = {};

    for (const field of ["name", "email"]) {
        if (!Object.hasOwn(payload, field)) {
            details.push(
                validationIssue(field, "required", "This field is required.")
            );
        }
    }

    // Collect independent field errors so a client can correct several
    // problems in one round trip.
    for (const [field, validator] of [
        ["name", value => validateString(value, "name", { min: 2, max: 80 })],
        ["email", validateEmail],
    ]) {
        if (!Object.hasOwn(payload, field)) continue;

        try {
            validated[field] = validator(payload[field]);
        } catch (error) {
            if (error instanceof ApiError) details.push(...error.details);
            else throw error;
        }
    }

    if (Object.hasOwn(payload, "age")) {
        try {
            validated.age = validateAge(payload.age);
        } catch (error) {
            if (error instanceof ApiError) details.push(...error.details);
            else throw error;
        }
    }

    if (details.length > 0) {
        throw new ApiError(
            422,
            "validation_failed",
            "One or more fields failed validation.",
            details
        );
    }

    return validated;
}

function parsePagination(searchParams) {
    const allowed = new Set(["limit", "offset"]);
    const details = [];

    for (const key of searchParams.keys()) {
        if (!allowed.has(key)) {
            details.push(
                validationIssue(
                    key,
                    "unknown_parameter",
                    "Query parameter is not supported."
                )
            );
        }
    }

    const parseBoundedInteger = (key, defaultValue, min, max) => {
        const raw = searchParams.get(key);

        if (raw === null) return defaultValue;

        // Strict decimal syntax avoids accepting values such as "1e2",
        // "2.5", whitespace, or partially numeric strings.
        if (!/^\d+$/.test(raw)) {
            details.push(
                validationIssue(
                    key,
                    "invalid_integer",
                    "Expected a non-negative decimal integer."
                )
            );
            return defaultValue;
        }

        const value = Number(raw);

        if (!Number.isSafeInteger(value) || value < min || value > max) {
            details.push(
                validationIssue(
                    key,
                    "out_of_range",
                    `Value must be between ${min} and ${max}.`
                )
            );
            return defaultValue;
        }

        return value;
    };

    const limit = parseBoundedInteger("limit", 20, 1, 100);
    const offset = parseBoundedInteger("offset", 0, 0, 1_000_000);

    if (details.length > 0) {
        throw new ApiError(
            422,
            "validation_failed",
            "One or more query parameters failed validation.",
            details
        );
    }

    return { limit, offset };
}

function parseJsonBody(raw) {
    if (raw.length === 0) {
        throw new ApiError(400, "empty_body", "A JSON body is required.");
    }

    try {
        return validateObject(JSON.parse(raw.toString("utf8")));
    } catch (error) {
        if (error instanceof ApiError) throw error;

        // Syntax details are intentionally not returned to external clients.
        throw new ApiError(
            400,
            "invalid_json",
            "The request body is not valid JSON."
        );
    }
}

class UserService {
    #users = new Map();
    #emailIndex = new Map();
    #nextId = 1;

    create(input) {
        const key = input.email.toLocaleLowerCase("en-US");

        if (this.#emailIndex.has(key)) {
            throw new ApiError(
                409,
                "email_conflict",
                "A user with this email address already exists.",
                [
                    validationIssue(
                        "email",
                        "already_exists",
                        "Email must be unique."
                    )
                ]
            );
        }

        const user = Object.freeze({
            id: this.#nextId++,
            name: input.name,
            email: input.email,
            age: input.age ?? null,
        });

        this.#users.set(user.id, user);
        this.#emailIndex.set(key, user.id);
        return user;
    }

    get(id) {
        const user = this.#users.get(id);

        if (!user) {
            throw new ApiError(
                404,
                "user_not_found",
                "The requested user does not exist."
            );
        }

        return user;
    }

    list({ limit, offset }) {
        return [...this.#users.values()]
            .sort((left, right) => left.id - right.id)
            .slice(offset, offset + limit);
    }
}

function serializeError(error, requestId) {
    if (error instanceof ApiError) {
        return {
            status: error.status,
            body: {
                error: {
                    code: error.code,
                    message: error.message,
                    details: error.details,
                    request_id: requestId,
                },
            },
        };
    }

    return {
        status: 500,
        body: {
            error: {
                code: "internal_server_error",
                message: "An unexpected error occurred.",
                details: [],
                request_id: requestId,
            },
        },
    };
}

function writeJson(response, status, body, requestId) {
    response.writeHead(status, {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Request-ID": requestId,
    });

    response.end(JSON.stringify(body));
}

function readBody(request, maxBytes = 16 * 1024) {
    return new Promise((resolve, reject) => {
        const chunks = [];
        let size = 0;
        let exceeded = false;

        request.on("data", chunk => {
            size += chunk.length;

            if (size > maxBytes) {
                exceeded = true;
                reject(
                    new ApiError(
                        413,
                        "payload_too_large",
                        "The request body exceeds the permitted size."
                    )
                );
                request.destroy();
                return;
            }

            chunks.push(chunk);
        });

        request.on("end", () => {
            if (!exceeded) resolve(Buffer.concat(chunks));
        });

        request.on("error", error => {
            reject(error);
        });
    });
}

function createServer() {
    const service = new UserService();

    return http.createServer(async (request, response) => {
        const requestId = randomUUID();

        try {
            const url = new URL(request.url, "http://localhost");
            const method = request.method.toUpperCase();

            if (method === "POST" && url.pathname === "/users") {
                const contentType = String(
                    request.headers["content-type"] || ""
                ).split(";")[0].trim().toLowerCase();

                if (contentType !== "application/json") {
                    throw new ApiError(
                        415,
                        "unsupported_media_type",
                        "Content-Type must be application/json."
                    );
                }

                const rawBody = await readBody(request);
                const input = validateCreateUser(parseJsonBody(rawBody));
                const user = service.create(input);

                writeJson(
                    response,
                    201,
                    { data: user, request_id: requestId },
                    requestId
                );
                return;
            }

            if (method === "GET" && url.pathname === "/users") {
                const pagination = parsePagination(url.searchParams);

                writeJson(
                    response,
                    200,
                    {
                        data: service.list(pagination),
                        pagination,
                        request_id: requestId,
                    },
                    requestId
                );
                return;
            }

            const match = url.pathname.match(/^\/users\/(\d+)$/);

            if (method === "GET" && match) {
                const id = Number(match[1]);

                if (!Number.isSafeInteger(id) || id < 1) {
                    throw new ApiError(
                        400,
                        "invalid_user_id",
                        "User ID must be a positive safe integer."
                    );
                }

                writeJson(
                    response,
                    200,
                    { data: service.get(id), request_id: requestId },
                    requestId
                );
                return;
            }

            throw new ApiError(
                404,
                "route_not_found",
                "The requested API route does not exist."
            );
        } catch (error) {
            const result = serializeError(error, requestId);

            if (!(error instanceof ApiError)) {
                // Server logs retain diagnostics; the client receives no
                // stack trace, database detail, or internal exception text.
                console.error("Request failed", requestId, error);
            }

            if (!response.headersSent && !response.destroyed) {
                writeJson(response, result.status, result.body, requestId);
            }
        }
    });
}

async function runExamples() {
    const service = new UserService();

    const examples = [
        {
            label: "Valid request",
            action: () => service.create(
                validateCreateUser({
                    name: "Ravi Sharma",
                    email: "ravi@example.com",
                    age: 31,
                })
            ),
        },
        {
            label: "Invalid email",
            action: () => validateCreateUser({
                name: "Ravi Sharma",
                email: "invalid",
            }),
        },
        {
            label: "Invalid numeric boundary",
            action: () => validateCreateUser({
                name: "Ravi Sharma",
                email: "ravi2@example.com",
                age: 17,
            }),
        },
        {
            label: "Unknown field",
            action: () => validateCreateUser({
                name: "Ravi Sharma",
                email: "ravi3@example.com",
                superuser: true,
            }),
        },
    ];

    for (const example of examples) {
        try {
            console.log(example.label, example.action());
        } catch (error) {
            console.log(
                example.label,
                serializeError(error, randomUUID())
            );
        }
    }

    const server = createServer();
    const port = Number(process.env.PORT || 3000);

    server.listen(port, "127.0.0.1", () => {
        console.log(`API listening on http://127.0.0.1:${port}`);
        console.log("POST /users, GET /users, GET /users/:id");
    });

    // Graceful shutdown prevents the server from retaining open handles.
    const shutdown = () => {
        server.close(error => {
            if (error) {
                console.error("Shutdown failed", error);
                process.exitCode = 1;
            }
        });
    };

    process.once("SIGINT", shutdown);
    process.once("SIGTERM", shutdown);
}

if (require.main === module) {
    runExamples().catch(error => {
        console.error("Application startup failed", error);
        process.exitCode = 1;
    });
}

module.exports = {
    ApiError,
    UserService,
    validateCreateUser,
    parsePagination,
    serializeError,
};
