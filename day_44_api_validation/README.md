# API Validation and Error Responses

## Purpose

API validation determines whether a request has the structure, types, values, and permissions required for an operation. Error-response design communicates failures in a consistent format so that clients can distinguish malformed requests, invalid fields, authentication failures, authorization failures, resource conflicts, missing resources, and unexpected server errors.

These are related responsibilities, but they are not interchangeable. Validation establishes whether supplied data satisfies the API contract. Error handling translates failures into appropriate HTTP responses. Authorization determines whether the caller may perform the operation. Database constraints preserve data integrity even when requests arrive concurrently or an application-level check is bypassed.

The implementations model device registration and user registration to demonstrate these responsibilities through executable code.

## Validation boundaries

A reliable API validates requests at several distinct boundaries.

| Boundary | Responsibility | Typical failure |
|---|---|---|
| HTTP request parsing | Read the body, interpret the media type, and parse JSON | Malformed JSON or unsupported content type |
| Structural validation | Require the expected object and field names | Array supplied instead of an object, missing field, unknown field |
| Type validation | Verify that values have the expected data types | String supplied where an integer is required |
| Field validation | Enforce length, range, format, and normalization rules | Invalid email or out-of-range firmware version |
| Domain validation | Enforce rules involving existing application state | Duplicate device name |
| Authorization | Check the caller's identity and permissions | Authenticated read-only client attempts registration |
| Persistence validation | Preserve integrity at the database boundary | Duplicate key or violated check constraint |
| Response mapping | Convert a known failure into an appropriate HTTP response | Validation failure returned as an unexplained server error |

Each boundary protects against a different class of failure. A syntactically valid JSON document can still contain invalid data. A valid request can still be unauthorized. A request that passes application checks can still conflict with a concurrent transaction.

## HTTP status semantics

The status code should describe the nature of the failure rather than the implementation detail that happened to detect it.

| Status | Meaning in these implementations | Example |
|---|---|---|
| `200 OK` | A read operation succeeded | Retrieve registered devices |
| `201 Created` | A resource was created successfully | Register a device or create a user |
| `400 Bad Request` | The request cannot be parsed or interpreted as required | Malformed JSON |
| `401 Unauthorized` | Authentication is missing or invalid | No active API client |
| `403 Forbidden` | The caller lacks permission | Read-only client attempts registration |
| `404 Not Found` | The requested route or resource does not exist | Unknown device ID |
| `409 Conflict` | The operation conflicts with existing state | Duplicate device name or email |
| `413 Content Too Large` | The request body exceeds the accepted limit | Oversized JSON payload |
| `415 Unsupported Media Type` | The body uses an unsupported media type | Plain text sent to a JSON endpoint |
| `422 Unprocessable Content` | The request is understood but violates field or domain validation rules | Firmware version outside the permitted range |
| `500 Internal Server Error` | An unexpected server-side failure occurred | Unhandled persistence or application failure |

The exact choice between `400` and `422` depends on the API contract. These examples use `400` for malformed JSON and `422` for understood JSON containing invalid fields. Consistency across endpoints is more important than using different conventions for equivalent failures.

## Structured error responses

A field-level error should identify the field, provide a stable machine-readable code, and include a message suitable for the API consumer.

The implementations use an error envelope containing:

- `code`, a stable identifier that client applications can use for branching logic.
- `message`, a concise explanation of the failure.
- `details`, an array of field-specific violations where appropriate.
- `request_id`, a correlation identifier that links the response to server-side diagnostics.

An example validation response is represented in JSON as:

    {
      "error": {
        "code": "validation_failed",
        "message": "One or more fields failed validation.",
        "details": [
          {
            "field": "owner_email",
            "code": "invalid_email",
            "message": "Provide a valid owner email address."
          },
          {
            "field": "firmware_major",
            "code": "out_of_range",
            "message": "Firmware major version must be between 1 and 99."
          }
        ],
        "request_id": "a-request-correlation-id"
      }
    }

The identifier above illustrates the response structure rather than representing an actual request.

Clients should branch on stable error codes, not message text. Messages can be clarified or translated without changing the programmatic contract. Field paths should also be stable enough for clients to associate errors with form controls.

Error details must not contain credentials, access tokens, database connection strings, SQL statements, stack traces, or other internal diagnostic information. Detailed diagnostics belong in access-controlled server logs.

## Python implementation

The Python program models a small user-registration API using standard-library components.

### Request parsing and validation

`validate_json_object` checks that a body exists, decodes UTF-8, parses JSON, and rejects non-object JSON values. Malformed JSON is reported as a `400` response, while a valid JSON array is rejected by the structural validation boundary.

`validate_create_user` combines independent field errors so a client can correct multiple mistakes in one request. It rejects unsupported fields rather than silently accepting values such as `admin`. This prevents callers from accidentally believing that an unrecognized field has been applied.

The field validators enforce the following constraints:

- Names are trimmed and must contain between 2 and 80 characters.
- Email addresses are subject to a practical syntax check and a maximum length.
- Ages must be actual integers between 18 and 120. Python booleans are explicitly rejected because `bool` is a subclass of `int`.
- Website URLs must use HTTPS, include a hostname, and exclude embedded credentials.

The email check is intentionally limited. It does not prove that a mailbox exists, and a production registration workflow may require email verification. URL syntax checks also do not establish that a destination is safe to contact. A server that fetches user-provided URLs must separately defend against server-side request forgery.

### Domain conflicts and pagination

`UserRepository` maintains an email index for efficient duplicate detection. Email comparisons are case-insensitive in this demonstration. The repository returns `409 Conflict` when a duplicate address is detected.

`validate_pagination` rejects unsupported query parameters and values that do not use the accepted decimal-integer format. The limit is bounded to 100 records, and the offset has an upper limit to prevent excessively expensive requests.

The in-memory repository provides stable ID ordering. A production database should use deterministic ordering and consider cursor-based pagination for large or frequently changing datasets.

### Error mapping and tests

`UserAPI.handle` maps validation failures and known HTTP errors to consistent response objects. Unexpected exceptions are converted to a generic `500` response, avoiding exposure of internal exception text.

The included `unittest` cases exercise successful creation, invalid field combinations, Boolean-versus-integer handling, malformed JSON, duplicate addresses, missing resources, unsupported media types, invalid pagination, request identifiers, and unknown fields.

The in-memory repository is useful for demonstrating the contract, but it is not durable storage. Its duplicate check is not a substitute for a database uniqueness constraint under concurrent requests.

## JavaScript implementation

The JavaScript program uses Node.js and its standard library to demonstrate an event-driven HTTP boundary.

### Schema checks and asynchronous body handling

`readBody` consumes request chunks asynchronously and enforces a body-size limit. This matters because request bodies are streamed and may arrive in multiple chunks. A production deployment should also configure request timeouts and connection limits.

`parseJsonBody` separates JSON syntax errors from structural errors. `validateCreateUser` then enforces field types, required fields, allowed fields, and age boundaries.

JavaScript's `Object.hasOwn` checks whether a property was actually supplied. This distinction is important for fields that may be omitted. An omitted optional field and an explicitly supplied invalid value must not automatically be treated as equivalent.

### HTTP error boundary

`ApiError` carries the status, stable code, message, and structured details. `serializeError` translates known failures into the shared response contract. Unexpected errors receive a generic response, while server-side diagnostics are logged with the request identifier.

The HTTP handler demonstrates:

- JSON content-type enforcement before request processing.
- Request-size limits during asynchronous body reading.
- Registration through `POST /users`.
- Bounded listing through `GET /users?limit=20&offset=0`.
- Resource lookup through `GET /users/:id`.
- Stable JSON error envelopes and security-related response headers.

The example uses an in-memory service and listens on the loopback interface. It is a teaching implementation, not a production deployment. A production service needs a durable repository, authenticated principals, authorization policies, rate limiting, request timeouts, and monitoring.

## C++ repository case study

The C++ program represents a device-registration gateway for industrial equipment. The gateway receives device names, owner email addresses, and firmware major versions. It must reject invalid data, prevent duplicate registrations, and distinguish data errors from identity and permission failures.

### Typed validation results

`Result<T>` contains either a value or an `ApiError`. This makes success and failure explicit in function signatures rather than requiring callers to infer success from printed output or sentinel values.

`DeviceValidator` accepts a map of supplied fields and applies the device-registration contract. It detects missing fields, unknown fields, invalid lengths, malformed email syntax, control characters, and firmware values outside the supported range.

Firmware input is parsed with `std::stoll` inside exception handling. The implementation checks that the entire string was consumed and that the result lies within the domain's permitted range before converting it to `int`. This avoids silently accepting partial numeric strings or narrowing an out-of-range value.

The validator aggregates independent errors. It does not proceed to persistence if any validation rule fails.

### Registry and concurrency considerations

`DeviceRegistry` indexes devices by normalized name. Lookup and duplicate detection are expected constant time on average with an unordered map, although worst-case hash-table behavior can be worse.

The case study demonstrates normalization before duplicate detection. `Plant Sensor A` and `PLANT SENSOR A` therefore represent the same logical device name.

The registry is deliberately an in-memory, single-process component. It is not thread-safe, and its uniqueness check is not atomic across concurrent operations. A production implementation should use database uniqueness constraints or an equivalent transactional mechanism. Synchronization may also be required if a shared registry is accessed concurrently within one process.

### Authorization and response serialization

`RegistrationEndpoint` checks authentication and registration permission independently of field validation. Valid data must not grant a caller additional privileges.

The JSON serializer escapes quotes, backslashes, control characters, and other characters that require escaping. Error responses contain field details but do not expose internal exceptions.

The example distinguishes `401`, `403`, `404`, `409`, and `422`. This gives API clients a reliable way to decide whether to authenticate, request access, correct their data, or resolve a resource conflict.

## Java enterprise implementation

The Java program models device registration through explicit domain types and service boundaries.

### Domain model and validation policy

The `DeviceCommand` record represents validated registration input. The `Device` record represents a persisted device and records the principal that registered it.

`DeviceRequestValidator` performs schema checks and collects field violations. Firmware versions must be Java `Integer` values in the supported range. A floating-point value such as `4.0` is not silently accepted as an integer, even if it appears mathematically equivalent.

The validator rejects unknown fields, which is useful when an API must prevent clients from attempting to set server-controlled attributes. In a production HTTP application, JSON parser configuration and data-transfer-object binding should enforce the same contract.

### Authorization and service boundaries

`Principal` contains a subject and a set of permissions. `DeviceRegistrationService` requires `REGISTER_DEVICE` for registration and `READ_DEVICE` for lookup.

These checks are separate from input validation. A syntactically correct request from a read-only principal still receives `403 Forbidden`.

`DeviceRepository` maintains a normalized-name index. Synchronized methods serialize access to the in-memory maps and ID counter within this process. This protects those data structures from concurrent mutation in a single JVM, but it does not coordinate multiple application instances. A shared database constraint remains necessary in a distributed deployment.

### Exceptions and response serialization

`ApiException` carries an HTTP status, a stable error code, and structured violations. `ApiBoundary` converts expected exceptions into an `ApiResponse` and hides unexpected exception details behind a generic server error.

The code includes JSON string escaping because hand-built JSON must not allow quotes or control characters in input values to corrupt the response structure. Production applications should normally use a mature JSON library instead of maintaining their own serializer.

The implementation illustrates domain and error-handling behavior without requiring an external framework. It does not implement a real HTTP server or a production authentication mechanism.

## PostgreSQL data model

The SQL implementation separates API clients, request records, field errors, and registered devices.

### Relational structure

| Table | Purpose |
|---|---|
| `api_clients` | Stores client identity, active status, and registration permission |
| `api_requests` | Records request IDs, methods, routes, lifecycle state, and timestamps |
| `api_field_errors` | Stores field-specific public errors associated with requests |
| `devices` | Stores accepted registrations and the client responsible for each device |

Foreign keys associate requests with known clients and field errors with their originating requests. Deleting a request removes its field-error records through `ON DELETE CASCADE`.

The `request_state` enum restricts request states to `received`, `validated`, `rejected`, and `completed`. A check constraint ensures that completed and rejected requests have a completion timestamp, while newly received and validated requests do not.

### Constraints and normalization

The device table generates `normalized_name` from the trimmed, lowercased device name. A unique constraint prevents equivalent normalized names from being stored twice.

The database also enforces:

- Device-name length.
- Email length and a basic email shape.
- Firmware major version between 1 and 99.
- Nonblank client identifiers and display names.
- Supported HTTP methods and bounded request sizes.

These constraints preserve important invariants even if a future application endpoint omits a corresponding validation check.

The email constraint is a basic syntax check, not full standards compliance or proof of mailbox ownership. PostgreSQL cannot establish whether an email address is deliverable simply by checking its string representation.

### Registration function and transaction behavior

`register_device` is a PL/pgSQL function that checks the client identity and registration permission, records request state, validates the supplied values, detects duplicate names, inserts a device, and returns a status and stable error code.

The unique constraint remains the final authority for duplicate device names. The function's preliminary lookup provides a clear conflict response for ordinary cases, while `ON CONFLICT` handles a competing insert that wins the race.

The demonstration calls the function with valid input, duplicate input, a read-only client, invalid fields, and a disabled integration. Reporting queries then inspect request outcomes and aggregate field errors by code and field path.

The function is an illustrative persistence workflow. It does not parse HTTP JSON, authenticate bearer tokens, or send network responses. Those responsibilities remain with the API service.

## Validation and error-handling distinctions

### Syntax errors versus semantic errors

A syntax error means the request cannot be parsed according to the expected representation. Invalid JSON belongs in this category.

A semantic or field error occurs after parsing succeeds. Examples include an email with an invalid shape, an unknown field, or a firmware version outside its supported range.

Keeping these categories separate improves client behavior. A client cannot fix a missing comma through field-level form validation, while it can directly correct an invalid email address.

### Field validation versus domain conflicts

Field validation usually evaluates a value independently of stored application state. A firmware major version of `150` violates a fixed range.

A domain conflict depends on current state. A device name may be valid in isolation but already registered. Such conflicts should be handled separately from field-format errors, commonly with `409 Conflict`.

### Validation versus authorization

A valid payload does not imply permission to perform the requested operation. Authentication establishes the caller's identity; authorization evaluates the caller's rights. A registration endpoint should apply both checks independently of field validation.

Care is required when resource existence is sensitive. Some APIs intentionally return the same response for inaccessible and nonexistent resources to avoid exposing their existence.

### Client errors versus internal failures

Known request failures should have explicit status codes and stable error identifiers. Unexpected failures should be logged for operators and returned as generic `500` responses.

Returning stack traces or raw database exceptions can expose implementation details. Request identifiers connect a client-visible error with restricted server-side diagnostics without placing sensitive diagnostic information in the response.

## Edge cases and production considerations

### Input size and computational limits

Field limits alone do not prevent an attacker from submitting an enormous body. HTTP servers should enforce body-size limits while reading the stream, before parsing consumes excessive memory.

Pagination limits should be enforced on the server. An API should not trust a client to request a reasonable number of records.

### Normalization and uniqueness

Normalization rules must be consistent between application code and database constraints. Case folding, Unicode normalization, whitespace handling, and locale-specific behavior can affect whether two values are treated as equivalent.

The demonstrations use straightforward lowercase normalization for email or device-name uniqueness. Real identity systems must choose and document a normalization policy appropriate to their domain.

### Race conditions

An application-level duplicate check is not enough when two requests can arrive concurrently. Both requests may observe that a name is available before either inserts it.

A unique database constraint and transactional insert resolve this class of race. The application must translate the resulting constraint violation into a stable conflict response rather than treating it as an unexplained internal failure.

### Error stability and observability

Machine-readable codes should remain stable across releases. Human-readable messages can evolve, but clients should not rely on exact message strings for control flow.

Request IDs should be propagated into logs and traces. Logs must be access-controlled and should avoid retaining full sensitive payloads by default. Validation failures can be recorded as field paths and codes without storing passwords, tokens, or other secrets.

### Schema evolution

Adding a required field can break existing clients. Changes to validation rules should therefore be assessed as API-contract changes. Where backward compatibility matters, use explicit versioning or a migration period in which old and new representations are handled deliberately.

### Database and application responsibilities

The API layer owns HTTP parsing, content-type enforcement, authentication, response status mapping, and the public error contract. The database owns durable relational integrity and transactional guarantees. Domain services own business rules that require application state.

Duplicating a critical constraint in both the service and the database can be appropriate when the checks serve different purposes. The service can provide a helpful error message, while the database ensures that invalid state cannot be committed.

## Practical evaluation scenarios

The six implementations can be evaluated against a shared set of cases:

| Scenario | Expected behavior |
|---|---|
| Valid request with all required fields | Return a successful creation response |
| Malformed JSON | Return a request-parsing error without invoking domain logic |
| Missing required field | Return a structured validation error identifying the field |
| Wrong data type | Reject the value without unsafe coercion |
| Unknown field | Reject unsupported input instead of silently granting unintended behavior |
| Numeric value outside its range | Return a field-specific range violation |
| Duplicate normalized identifier | Return a conflict response and preserve existing data |
| Unauthenticated request | Return an authentication error |
| Authenticated request without permission | Return an authorization error |
| Missing resource | Return a not-found response |
| Oversized request | Reject the request before unrestricted body processing |
| Unexpected internal exception | Return a generic server error and retain diagnostics in server-side logs |

These cases test the API contract across parsing, validation, authorization, persistence, and response serialization. The same contract should be exercised in unit tests and integration tests against the actual HTTP server and database.
