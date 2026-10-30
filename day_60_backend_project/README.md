# Production-Style REST API

## System scope

This project implements a task-management REST API and examines the backend responsibilities required to expose application functionality through reliable HTTP interfaces.

The resource model is deliberately small. Its behavior is not. The implementations cover authentication, input validation, resource lifecycle, state transitions, idempotent creation, optimistic concurrency, pagination, rate limiting, persistence, error responses and operational logging.

The five implementations use different engineering approaches:

| Implementation | Primary responsibility | Runtime or platform |
|---|---|---|
| Python | HTTP service with transactional SQLite persistence | Python 3.10+ |
| JavaScript | Event-driven HTTP service and asynchronous request processing | Node.js 20+ |
| C++17 | Transport-neutral request pipeline and API service engine | C++17 |
| Java 17 | Enterprise-oriented HTTP service with explicit domain types | Java 17 |
| PostgreSQL | Relational persistence, transactional operations and database enforcement | PostgreSQL 13+ |

The Python, JavaScript and Java implementations provide HTTP servers. The C++ program models the request-processing and domain layers without implementing a socket-level HTTP parser. Its request structures represent the validated information an HTTP adapter would supply. The PostgreSQL script defines a database-oriented model for deployments in which authentication, task ownership and operational records must be persisted across multiple clients.

## REST resource model

The principal resource is a task.

A task contains:

| Field | Meaning |
|---|---|
| `id` | Unique resource identifier |
| `title` | Required task title |
| `description` | Optional descriptive text |
| `status` | Current task lifecycle state |
| `version` | Monotonically increasing resource version |
| `created_at` | Creation timestamp |
| `updated_at` | Most recent modification timestamp |

The supported task states are:

- `pending`: The task has been created but work has not started.
- `in_progress`: Work has started.
- `completed`: Work has finished.
- `cancelled`: The task has been stopped.

The permitted transitions are intentionally restricted:

| Current state | Permitted next states |
|---|---|
| `pending` | `in_progress`, `cancelled` |
| `in_progress` | `pending`, `completed`, `cancelled` |
| `completed` | None |
| `cancelled` | None |

A completed or cancelled task is terminal in this model. A request to move a terminal task into another state receives a conflict response rather than silently changing its history.

## HTTP interface

All application resources are under `/v1`. The `/health` endpoint is available without bearer authentication so that a local health probe can determine whether the HTTP service is responding.

| Method | Endpoint | Purpose | Success response |
|---|---|---|---|
| GET | `/health` | Service health | `200` |
| GET | `/v1/tasks` | List tasks | `200` |
| POST | `/v1/tasks` | Create a task | `201`, or `200` for an idempotent replay |
| GET | `/v1/tasks/{id}` | Retrieve one task | `200` |
| PATCH | `/v1/tasks/{id}` | Modify selected fields | `200` |
| DELETE | `/v1/tasks/{id}` | Delete a task | `200` |

The collection endpoint supports `status`, `limit` and `offset` query parameters. The default page size is 20, and the maximum is 100. Negative offsets, malformed numbers, unsupported statuses and values outside the permitted ranges are rejected.

An example collection request is:

`GET /v1/tasks?status=pending&limit=20&offset=0`

The response has a `data` array and a `pagination` object. The `returned` property indicates how many records were included in that particular page. It is not a total-record count.

### Request authentication

All `/v1` application routes require an HTTP bearer token:

`Authorization: Bearer <token>`

The services read the configured token from the `API_TOKEN` environment variable. The development default permits the code to run without a separate configuration step, but it must be replaced before deployment.

Python compares supplied credentials using `hmac.compare_digest`. JavaScript hashes both values and uses `crypto.timingSafeEqual`. Java compares fixed-length SHA-256 digests using `MessageDigest.isEqual`. The C++ example uses a comparison routine that does not return early when characters differ.

The C++ comparison is an educational control, not a replacement for a vetted authentication library or a production credential-management system.

The SQL model stores SHA-256 digests in `api_clients.key_hash`. The `authenticate_client` function accepts a digest supplied by the application and returns the active client's identifier. It does not store or return plaintext credentials.

## Request processing

The API request lifecycle is:

    HTTP Request
         |
         v
    Route identification
         |
         v
    Health endpoint or API authentication
         |
         v
    Rate-limit evaluation
         |
         v
    Content type and body-size checks
         |
         v
    JSON parsing and field validation
         |
         v
    Resource and policy validation
         |
         v
    Repository operation
         |
         v
    Structured HTTP response
         |
         v
    Request metadata logging

The actual order varies slightly between implementations. The common responsibilities remain separate:

- Routing identifies the resource and operation.
- Authentication determines whether the caller possesses a valid service credential.
- Rate limiting controls request volume.
- Validation checks the request representation and business rules.
- Repository operations enforce data consistency.
- Response handling maps application outcomes to HTTP status codes.
- Logging records operational metadata without recording bearer tokens or request bodies.

Authentication alone does not establish fine-grained authorization. A multi-user production deployment must associate authenticated clients with resource ownership and permissions. The SQL implementation demonstrates client-to-task ownership through `client_id`.

## Request validation

The API accepts JSON objects with string-valued fields.

Creation supports:

| Field | Rule |
|---|---|
| `title` | Required, non-empty after trimming, maximum 160 characters |
| `description` | Optional, maximum 2,000 characters |

Modification supports `title`, `description` and `status`. Unknown fields are rejected rather than ignored. An empty PATCH request is invalid.

The services enforce an upper request-body size of 1 MiB. The Python and Java implementations also verify the request content type before parsing. JavaScript checks the received stream size while reading it, rather than trusting only the declared `Content-Length`.

The Java implementation contains a bounded JSON object parser because Java 17 does not include a general-purpose JSON API in its standard library. It accepts string-valued object properties, supports JSON string escapes, rejects duplicate keys and rejects nested values. This is a constrained request format, not a general-purpose JSON parser. A production application should use a maintained JSON library.

The C++ program receives parsed request fields through its `Request` structure. A real HTTP adapter must enforce equivalent JSON, encoding, content-type and body-size checks before constructing that structure.

## Idempotent resource creation

A network request can reach the server even when the client does not receive its response. Retrying an ordinary POST in that situation may create duplicate resources.

The API requires an `Idempotency-Key` header for task creation. A key must contain between 8 and 128 permitted characters.

The service associates the key with a canonical representation of the validated request:

    Client request
         |
         v
    Validate title and description
         |
         v
    Canonical request representation
         |
         v
    Calculate request fingerprint
         |
         v
    Look up client key
         |
         +---- Existing key, same payload
         |          |
         |          v
         |      Return original task
         |
         +---- Existing key, different payload
         |          |
         |          v
         |      Return conflict
         |
         +---- New key
                    |
                    v
                Create task
                    |
                    v
                Store key and result

A repeated request with the same key and same payload returns the original task. A reused key with a different payload produces `409 Conflict`. New keys are retained for 24 hours in the Python, JavaScript and Java implementations.

The Python implementation performs the key lookup and resource insertion inside a SQLite `BEGIN IMMEDIATE` transaction. This serializes competing SQLite writers during the creation sequence.

The JavaScript implementation performs its in-memory lookup and insertion synchronously on the event loop. The Java implementation synchronizes the repository creation operation. The C++ implementation protects its repository with a mutex.

The PostgreSQL function uses a primary-key constraint on `(client_id, idempotency_key)`, an insert with `ON CONFLICT`, and a row lock before deciding whether to create or return the task. The SQL model scopes idempotency keys to individual clients.

Idempotency is not a replacement for authorization. A production implementation should also define retention, cleanup, payload canonicalization, key ownership and behavior after resource deletion.

## Optimistic concurrency

Two clients can retrieve the same resource and then attempt to modify it. Without concurrency control, the later write may silently overwrite the earlier change.

Every task therefore has a `version` value. New tasks start at version 1. A successful modification increments the version.

A client retrieves a task and receives an ETag, for example:

`ETag: "1"`

The client must supply that value in the next modification request:

`If-Match: "1"`

The service compares the supplied version with the stored version before updating or deleting the resource.

| Condition | HTTP status | Meaning |
|---|---:|---|
| No `If-Match` header | `428` | Required precondition is missing |
| Malformed version | `400` | Invalid conditional request |
| Resource has changed | `412` | Client's representation is stale |
| State transition is prohibited | `409` | Request conflicts with domain rules |
| Resource does not exist | `404` | No matching task is available |

The distinction between `409` and `412` is important. A `409` indicates a domain conflict, such as an invalid task transition. A `412` indicates that the client's concurrency precondition is no longer satisfied.

Python uses a conditional SQL update with both the identifier and expected version in its `WHERE` clause. The JavaScript store checks and replaces a resource in one synchronous operation. The Java store synchronizes modification methods. The C++ repository uses a mutex. PostgreSQL locks the selected row with `FOR UPDATE` and uses a trigger to increment the version.

## Error representation

Errors use a consistent response structure:

    {
      "error": {
        "code": "version_conflict",
        "message": "The task changed. Retrieve its latest version."
      },
      "request_id": "request-identifier"
    }

The implementations use explicit status codes rather than returning a successful status for failed operations.

| Status | Use |
|---:|---|
| `400` | Invalid JSON, fields, values or query parameters |
| `401` | Missing or invalid bearer credential |
| `404` | Unknown route or resource |
| `405` | Unsupported method for a resource |
| `411` | Required content length missing in the Python service |
| `412` | Stale resource version |
| `413` | Request body exceeds the configured size |
| `415` | Unsupported content type |
| `428` | Required conditional request header missing |
| `429` | Rate limit exceeded |
| `500` | Unexpected application failure |
| `503` | Database operation unavailable in the Python service |

The response includes a request identifier, allowing a failed operation to be correlated with server logs without logging the credential or body.

## Python implementation

The Python file implements a working HTTP API using `ThreadingHTTPServer` and SQLite.

Its principal components are:

| Component | Responsibility |
|---|---|
| `TaskStatus` | Restricts task states to an enumeration |
| `ApiError` | Carries an HTTP status, error code and safe message |
| `RateLimiter` | Enforces a thread-safe sliding-window limit |
| `TaskRepository` | Owns SQLite operations and transaction boundaries |
| `TaskApiHandler` | Parses HTTP requests, validates input and routes operations |
| `TaskApiServer` | Provides shared repository, token and rate-limiter state |

A database connection is created per operation. SQLite's write-ahead logging mode improves reader/writer concurrency, and foreign-key enforcement is enabled on each connection.

The repository uses parameterized SQL for all variable data. Dynamic SQL is limited to values selected from a fixed set of validated fields. The idempotent creation workflow begins an immediate transaction before checking or inserting the idempotency key.

The handler uses typed validation functions for titles, descriptions, statuses, pagination and conditional versions. It returns a safe error response for database failures and records a request identifier with timing information.

The API binds to `127.0.0.1` by default. `API_HOST`, `API_PORT`, `API_DB_PATH`, `API_TOKEN` and `LOG_LEVEL` are configurable through environment variables.

## JavaScript implementation

The JavaScript file uses Node.js's native HTTP server, cryptographic functions and event emitter.

Its main components are:

| Component | Responsibility |
|---|---|
| `SlidingWindowRateLimiter` | Tracks request timestamps for each client address |
| `TaskStore` | Manages resources and idempotency records |
| `AuditEvents` | Emits structured request metadata |
| `readJson` | Reads and limits asynchronous request streams |
| `routeRequest` | Applies routing, authentication and resource behavior |
| HTTP server | Manages incoming connections and response lifecycle |

The request handler is asynchronous because reading an HTTP body is an asynchronous stream operation. The task-store modifications are synchronous in this implementation, so an idempotency lookup and insertion cannot be interleaved by another event-loop callback.

`EventEmitter` separates request completion from audit output. Audit records include the request identifier, method, route, status and duration, but do not include bearer tokens or request bodies.

The implementation uses `crypto.randomUUID` for resource identifiers and SHA-256 digests for fixed-length token comparison. The use of an in-memory store makes this implementation suitable for local execution and architecture study. It is not durable across restarts and does not coordinate state across multiple Node.js processes.

The server handles `SIGINT` and `SIGTERM` by closing the listener and then closing remaining connections after a bounded interval.

## C++17 implementation

The C++ program focuses on the API's transport-neutral request-processing and domain layers.

Its domain types include `Task`, `Request`, `Response`, `TaskStatus` and `ApiError`. The `TaskRepository` owns task state, conditional updates and idempotency behavior. `RateLimiter` protects shared request buckets with a mutex. `ApiGateway` applies authentication, rate limits, routing and business validation.

The request object contains normalized headers, parsed fields and query parameters. This separation is useful when an HTTP framework or gateway is responsible for network transport and JSON decoding.

The program uses:

- `std::unordered_map` for indexed task and idempotency lookup.
- `std::map` for deterministic request fields and headers.
- `std::vector` for rate-limit timestamps and paginated results.
- `std::optional` for an optional status filter.
- `std::mutex` for shared repository and rate-limit state.
- `std::chrono` for monotonic rate-limit measurement.
- `std::variant`-like explicit enum behavior through `TaskStatus`.
- Structured exceptions for predictable HTTP error mapping.

The implementation uses an in-memory repository and illustrative task identifiers. The fingerprint used by its idempotency store is direct canonical field content rather than a cryptographic digest. A production adapter should use a cryptographic hash, durable persistence, a proven authentication mechanism and a maintained HTTP/JSON library.

## Java 17 implementation

The Java file provides a runnable HTTP service using `com.sun.net.httpserver.HttpServer`.

The domain model uses a `Task` record, while `TaskStore` synchronizes resource mutations. `CreateResult` and `IdempotencyEntry` model the outcome and stored state of idempotent creation. `ApiException` carries controlled HTTP error information.

Java-specific design decisions include:

- Records for immutable resource and operation data.
- `ConcurrentHashMap` for shared task and idempotency indexing.
- Synchronized repository methods for atomic multi-step operations.
- Streams for filtering, ordering and pagination.
- `MessageDigest` for SHA-256 token digests.
- `MessageDigest.isEqual` for digest comparison.
- A bounded custom JSON parser to avoid third-party dependencies.
- `ExecutorService` for concurrent HTTP request handling.
- A shutdown hook for controlled server termination.

The custom JSON parser accepts only objects whose values are strings. It rejects duplicate keys, nested structures and trailing content. The limitation is explicit, so a production implementation should replace it with a full JSON library if the resource contract expands.

The HTTP server listens on `127.0.0.1` by default and uses a fixed-size worker pool. The in-memory repository is suitable for a single-process demonstration, not a horizontally scaled service.

## PostgreSQL implementation

The SQL file provides a relational model for a multi-client backend API.

| Database object | Responsibility |
|---|---|
| `api_clients` | Stores client metadata, key digests and rate-limit policy |
| `tasks` | Stores client-owned task resources |
| `idempotency_records` | Associates request keys with payload fingerprints and task results |
| `request_audit` | Records request metadata and outcome |
| `rate_limit_windows` | Tracks request counts for time windows |
| `task_dashboard` | Aggregates task counts by client and state |
| `request_error_report` | Aggregates failed requests by route and status |

The `tasks` table associates every resource with a client. The composite foreign key from idempotency records to `(task_id, client_id)` prevents an idempotency record from referencing a task owned by a different client.

The `touch_task_version` trigger increments the version and updates the timestamp when relevant task fields change. This keeps version maintenance at the database boundary, including for updates made outside the HTTP application.

`create_task` establishes an idempotency record before creating a resource. Its unique key and row lock provide transactional coordination for concurrent attempts using the same client and key.

`transition_task_status` locks the task row, checks client ownership, verifies the expected version and validates the state transition. It raises distinct SQLSTATE values for stale versions, invalid transitions and unavailable resources.

`consume_rate_limit` atomically increments a per-client time-window counter only while the configured threshold has not been reached. `evaluate_client_request` provides a separate read-only eligibility check.

The sample data includes an active integration, an inactive integration, tasks in different states, an idempotency record, request-audit events and a rate-limit bucket. The script also executes valid and invalid transition examples inside exception-handling blocks.

The script uses `CREATE IF NOT EXISTS` and fixed sample identifiers to make its sample model repeatable. It does not remove an existing schema. It should still be tested against a dedicated database before execution in an environment containing operational data.

## API state and failure handling

The main failure paths are distinct:

| Failure | Detection point | Result |
|---|---|---|
| Invalid credential | Authentication middleware | `401` |
| Excess request volume | Rate limiter | `429` |
| Invalid JSON | Request parser | `400` |
| Wrong content type | Request parser | `415` |
| Excessive body size | Request reader | `413` |
| Reused idempotency key with different payload | Repository | `409` |
| Stale resource version | Repository or database | `412` |
| Prohibited status transition | Domain validation | `409` |
| Unknown resource | Repository | `404` |
| Database failure | Persistence boundary | `503` in Python |

The services avoid exposing internal exception messages or database details through general server-error responses. Detailed diagnostics belong in restricted logs, not in responses sent to clients.

## Operational and security boundaries

The implementations are executable reference services. They establish important backend behavior, but they do not claim to replace a complete production deployment.

A production environment should provide:

- TLS termination and secure proxy configuration.
- A secret manager for API credentials and database passwords.
- Credential rotation and client revocation.
- Durable database-backed task storage.
- Database migrations and schema-version management.
- Connection pooling and bounded database timeouts.
- Distributed rate limiting for multiple service instances.
- Authorization scopes and client-level resource isolation.
- Centralized structured logs, metrics and tracing.
- Health checks that distinguish process health from dependency health.
- Backup, restoration and retention procedures.
- Request correlation across gateways, application services and databases.
- Explicit CORS policy where browser clients require cross-origin access.
- Idempotency cleanup and retention policies.
- Pagination strategies suitable for large datasets.
- Monitoring for repeated authentication failures and unusual request patterns.

The Python service persists task data locally but uses an in-memory rate limiter and a single configured bearer token. The JavaScript and Java examples use in-memory task stores and are not restart-durable. The C++ implementation is a domain and request-pipeline model rather than a network server. The PostgreSQL schema demonstrates multi-client persistence and database-side enforcement, but the application files do not connect to that schema.

A deployment that combines these components should use one authoritative persistence layer, one consistent authentication model and shared concurrency semantics. In-memory examples must not be treated as distributed coordination mechanisms.

## Running the implementations

### Python

Save the first file as `app.py`.

Run with the default development configuration:

`python app.py`

Configure the service before deployment:

`API_TOKEN=<strong-secret> API_PORT=8080 API_DB_PATH=tasks_api.db python app.py`

The Python implementation uses only the standard library.

### JavaScript

Save the second file as `server.js`.

Run:

`node server.js`

Configure the token with the `API_TOKEN` environment variable. The implementation uses Node.js native modules and does not require an npm installation.

### C++17

Save the third file as `main.cpp`.

Compile:

`g++ -std=c++17 -O2 -pthread -Wall -Wextra -pedantic main.cpp -o rest_api_engine`

Run:

`./rest_api_engine`

The executable runs a series of request-processing scenarios and prints each response.

### Java 17

Save the fourth file as `RestApiServer.java`.

Compile:

`javac --add-modules jdk.httpserver RestApiServer.java`

Run:

`java --add-modules jdk.httpserver RestApiServer`

The server uses the JDK HTTP server module and does not require third-party dependencies.

### PostgreSQL

Save the fifth file as `schema.sql`.

Execute against a dedicated PostgreSQL database:

`psql -d backend_development -v ON_ERROR_STOP=1 -f schema.sql`

The script creates the `backend_api` schema, defines its database objects, inserts sample data, exercises database functions and reports sample results.

## Exercising the HTTP workflow

The following commands use the default development token and the Python or JavaScript service.

Check health:

`curl http://127.0.0.1:8080/health`

Create a task:

`curl -i -X POST http://127.0.0.1:8080/v1/tasks -H "Authorization: Bearer local-development-token" -H "Content-Type: application/json" -H "Idempotency-Key: create-task-0001" -d "{\"title\":\"Implement API authentication\",\"description\":\"Validate bearer credentials.\"}"`

List tasks:

`curl -i "http://127.0.0.1:8080/v1/tasks?limit=20&offset=0" -H "Authorization: Bearer local-development-token"`

Retrieve a task:

`curl -i http://127.0.0.1:8080/v1/tasks/TASK_ID -H "Authorization: Bearer local-development-token"`

Modify a task using its current ETag version:

`curl -i -X PATCH http://127.0.0.1:8080/v1/tasks/TASK_ID -H "Authorization: Bearer local-development-token" -H "Content-Type: application/json" -H "If-Match: \"1\"" -d "{\"status\":\"in_progress\"}"`

Delete a task using its current version:

`curl -i -X DELETE http://127.0.0.1:8080/v1/tasks/TASK_ID -H "Authorization: Bearer local-development-token" -H "If-Match: \"2\""`

Replace `TASK_ID` and the ETag version with the values returned by the service. A stale version should produce `412`, while a prohibited state transition should produce `409`.

## Design limitations

The project deliberately separates HTTP mechanics from domain rules and persistence responsibilities, but it does not implement every concern required by a large production platform.

The HTTP services use a single configured bearer token rather than a complete client identity provider. The Python and JavaScript services do not use the PostgreSQL schema as their persistence layer. The JavaScript and Java stores are not durable. The C++ program does not parse HTTP wire data or establish network connections. The SQL model demonstrates database-side integrity but does not provide a complete migration history.

These boundaries matter when evaluating correctness. A working local HTTP endpoint is not, by itself, proof of production readiness. Production readiness also requires operational controls, security testing, deployment validation, failure recovery and consistent behavior across all running service instances.
