# Backend Fundamentals: Servers, Routing, and Middleware

## Scope

This project models the three foundational mechanisms that connect an HTTP request to backend application behavior:

- A **server** accepts network requests, constructs request context, invokes application code, and sends HTTP responses.
- **Routing** determines which endpoint handler should process a request based on the HTTP method and requested path.
- **Middleware** surrounds request handling with reusable cross-cutting behavior such as request identification, authentication, authorization, logging, timing, payload limits, and security headers.

These mechanisms are related but not interchangeable. The server provides the execution boundary, the router selects endpoint behavior, and middleware controls processing around that behavior.

The implementations deliberately use different technical perspectives rather than translating the same program into five languages.

## Core Request Lifecycle

A backend request can be viewed as a pipeline:

`client -> server -> request parsing -> middleware -> routing -> handler -> response middleware -> HTTP response`

A server is responsible for the transport boundary. It receives method, target, headers, and body data and ultimately writes a status code, response headers, and response body.

Routing answers a narrower question:

`Which handler owns this method and path?`

Middleware answers another question:

`What processing must occur before or after the selected handler?`

For example, authentication middleware may reject an unauthenticated request before a protected handler runs. Timing middleware can measure the complete downstream operation without embedding timing code into every endpoint.

## HTTP Server Fundamentals

The Python implementation uses `ThreadingHTTPServer` and `BaseHTTPRequestHandler`. The server creates a request object from the incoming HTTP message and passes it into the application pipeline.

The Python request model explicitly separates:

- HTTP method
- target URI
- parsed path
- query parameters
- headers
- body
- remote address
- route parameters
- middleware context

The response model similarly separates status, headers, and body.

The Node.js implementation uses the standard `node:http` module. This exposes an important backend distinction: request bodies arrive as streams. The `readBody` function therefore collects chunks and enforces a maximum payload size rather than assuming the complete body is already available.

The Java and C++ implementations model the same server boundary without introducing a third-party HTTP framework. This makes the application architecture visible even though their examples use controlled requests instead of opening a production network listener.

## Servers and Responsibility Boundaries

A server should not become the place where all application logic is implemented.

The implementations maintain separate responsibilities:

| Layer | Responsibility |
| --- | --- |
| HTTP server | Accept requests and produce HTTP responses |
| Request model | Represent method, path, headers, body, and context |
| Middleware | Apply cross-cutting request policies |
| Router | Match method and path to a handler |
| Handler | Execute endpoint-specific behavior |
| Repository/store | Manage domain data |
| Error boundary | Convert failures into controlled HTTP responses |

This separation makes backend systems easier to test and reason about. A routing test does not need a database, while a repository test does not need a network socket.

## Routing Mechanics

Routing has two fundamental inputs:

`HTTP method + request path`

A route such as `/users` may represent a collection resource, while `/users/:id` represents an individual resource identified by a path parameter.

The Python router uses patterns such as `/users/{user_id}`. The JavaScript, C++, and Java routers use `:id`-style parameters.

A parameterized route must capture the dynamic portion of the path without consuming additional path segments. A route matching `/users/:id` should match `/users/1001` but not `/users/1001/orders`.

### Static and Parameterized Routes

Route precedence matters when patterns overlap.

A static route such as `/health` is more specific than a broad parameterized route such as `/:resource`. The implementations therefore calculate a static-route score and prefer routes with more literal path segments.

Without explicit precedence, a generic parameter route can accidentally capture requests intended for a more specific endpoint.

### Method Matching

Routing is not only path matching.

`GET /users` and `POST /users` can represent completely different operations even though their paths are identical.

The routers therefore match both method and path. When the path exists but the HTTP method does not, the appropriate backend response is `405 Method Not Allowed`, with an `Allow` header where applicable.

When neither path nor method matches a registered route, the request becomes `404 Not Found`.

## Path Parameters and Query Parameters

Path parameters identify resources:

`/users/1001`

Here, `1001` is part of the resource path.

Query parameters modify retrieval behavior without changing the resource identity:

`/users?role=reviewer`

The Python implementation uses `parse_qs`, while the JavaScript implementation uses the standard `URL` class.

These mechanisms have different semantics. Treating query parameters and path parameters as interchangeable can produce confusing APIs and ambiguous authorization rules.

## Middleware Architecture

Middleware is one of the most important backend design patterns demonstrated by the implementations.

A middleware receives a downstream handler and returns another handler. This creates an execution chain.

Conceptually:

`middleware A -> middleware B -> middleware C -> handler`

A request passes inward through the chain. The response then travels outward.

The implementations use composition rather than copying authentication, logging, or timing logic into every endpoint.

This makes middleware particularly suitable for policies that apply across many routes.

## Request Identification

Request IDs allow logs and responses to be correlated.

The implementations accept a bounded client-supplied `X-Request-ID` where appropriate and generate an identifier when one is missing or invalid.

The identifier is placed into request context and returned through the `X-Request-ID` response header.

A production implementation should define a clear policy for trusted correlation IDs. Arbitrarily accepting long or malformed values can create logging problems and unnecessarily large request metadata.

## Logging and Timing Middleware

Logging middleware measures request duration and records the HTTP method, path, response status, and request ID.

Timing is implemented differently across the languages:

- Python uses `time.perf_counter()`.
- JavaScript uses `process.hrtime.bigint()`.
- C++ uses `std::chrono::steady_clock`.
- Java uses `Instant` and `Duration`.
- PostgreSQL stores request duration in microseconds for later operational analysis.

A monotonic clock is preferable for duration measurements because wall-clock adjustments should not make an operation appear to run backward or forward unexpectedly.

## Authentication and Authorization

Authentication establishes who is making the request.

Authorization determines whether the authenticated principal may perform the requested operation.

The examples distinguish these stages.

The protected user-creation endpoint first requires authentication and then requires the `admin` role. An ordinary authenticated user therefore fails authorization rather than authentication.

The demonstration credentials are intentionally deterministic examples. They are not appropriate production secrets.

A real backend should not hard-code bearer tokens in source code. Credentials should be securely issued, stored, rotated, expired, revoked, and validated.

## Error Handling

Backend errors should become controlled HTTP responses rather than leaking internal exceptions.

The implementations distinguish common failure classes:

- `400` for invalid client input
- `401` for missing or invalid authentication
- `403` for insufficient authorization
- `404` when no resource or route exists
- `405` when the path exists but the HTTP method is unsupported
- `413` when a request body exceeds the configured limit
- `415` when the request uses an unsupported media type
- `500` for unexpected server failures

The Python and JavaScript applications contain centralized error boundaries. The C++ and Java examples use typed exceptions to represent HTTP failures.

A production service should avoid exposing stack traces, database credentials, internal filesystem paths, or other implementation details in client-facing error messages.

## Python Implementation

The Python program provides the most complete low-level server demonstration.

Its `ThreadingHTTPServer` creates a real local HTTP server. The request handler parses the URL, headers, content length, and body before constructing the application request.

The `RoutePattern` class turns route patterns such as `/users/{user_id}` into regular expressions and extracts named parameters.

`Router` maintains method-specific routes and uses static-route precedence to reduce ambiguity.

The application also contains:

- request ID middleware
- security-header middleware
- body-size enforcement
- request logging
- bearer authentication
- role-based authorization
- in-memory user storage
- JSON parsing
- validation
- `Location` headers for created resources
- centralized unexpected-error handling
- graceful server shutdown

The body-size middleware is important because accepting unlimited request bodies can make a server vulnerable to resource exhaustion.

The server can be run directly with Python. It exposes `/health`, `/users`, `/users/{id}`, and protected administrative operations.

## JavaScript Implementation

The JavaScript implementation focuses on Node.js backend behavior.

The use of `node:http` instead of Express makes several mechanisms explicit.

HTTP request bodies are streams, so `readBody` listens for `data`, `end`, and `error` events. It also stops processing when the configured maximum body size is exceeded.

The `Router` class supports:

- HTTP method matching
- static routes
- parameterized routes
- parameter extraction
- route precedence
- `405` detection

The middleware chain demonstrates JavaScript's functional composition model. Authentication and authorization are attached only to endpoints that require them.

The server also demonstrates asynchronous endpoint execution through `async` handlers and a graceful shutdown path using `SIGINT` and `SIGTERM`.

This is particularly useful for understanding why Node.js backend code frequently represents request processing with promises and asynchronous functions.

## C++ Case Study

The C++ implementation models a repository-style backend as a layered request-processing system.

The major components are:

- `Request` for incoming request state
- `Response` for HTTP output
- `Route` for pattern matching
- `Router` for method and path dispatch
- `UserStore` for domain persistence
- middleware functions for request policy
- `HttpError` for controlled HTTP failures

The router uses `std::regex` to capture dynamic path parameters.

Route candidates are ordered by their number of static segments, giving more specific routes precedence over generic parameterized routes.

The middleware composition function uses `std::function` to construct an onion-style handler chain.

The domain store validates user names and roles before insertion. This keeps domain constraints out of the router itself.

The case study also demonstrates response timing with `std::chrono::steady_clock`, which is suitable for elapsed-time measurements.

The controlled request scenarios cover healthy requests, successful resource retrieval, missing resources, failed authorization, successful administrative creation, and deletion.

## Java Enterprise-Oriented Model

The Java implementation emphasizes explicit domain types and service boundaries.

`HttpRequest` and `HttpResponse` are records representing transport-level values.

`Route` captures method, path pattern, parameter names, static specificity, and its handler.

`Router` separates route resolution from endpoint execution.

`UserRepository` is an interface rather than a concrete dependency inside every handler. `InMemoryUserRepository` supplies the current implementation. This makes the domain layer less dependent on storage details.

`AuthenticationService` owns credential interpretation.

Role enforcement is represented through `requireRole`, making authorization a reusable policy rather than a collection of repeated conditionals.

Java's immutable `record` types are useful for request and domain values because they make data ownership and structure explicit.

The program also uses `Optional` for repository lookup, avoiding an implicit `null` result when a user does not exist.

## SQL Data Model

The PostgreSQL implementation treats backend execution as an observable relational workflow.

`api_routes` stores route definitions and their authentication policy.

`api_users` stores principals and roles.

`api_tokens` stores token fingerprints rather than raw bearer credentials.

`http_requests` records the relationship between incoming requests, selected routes, users, response status, response size, and execution time.

`middleware_execution` records which middleware ran and whether a middleware blocked the request.

`request_errors` records controlled failures.

The relationships allow operational questions to be answered without parsing application logs alone.

## Database-Level Integrity

The SQL script uses constraints to protect data quality.

The `api_routes` table prevents a route from declaring a required role while authentication is disabled.

The user table enforces non-empty display names and valid username lengths.

HTTP response status values are restricted to the valid HTTP range.

Middleware execution durations cannot be negative.

Token expiration and revocation timestamps are checked against issuance time.

These rules are valuable because application-level validation can be bypassed by another service, administrative operation, migration, or future application version. Durable invariants should be enforced at the database layer when appropriate.

## Database Indexing

Indexes support common backend lookup patterns.

The route index supports method, enabled-state, and path-based lookup.

Request indexes support:

- route-level operational metrics
- status-based failure analysis
- user-specific request history

The token index uses a partial condition so active-token lookups do not require indexing revoked records in the same way.

Indexes should correspond to actual query patterns. Adding indexes indiscriminately increases storage consumption and write overhead.

## Transactions

The SQL script demonstrates a transaction that records a request, records middleware execution, and then completes the request.

The purpose is consistency between related operational records.

If a workflow requires several database mutations to represent one logical operation, committing only part of that operation can create misleading operational state.

Transactions provide an atomic boundary, but they should not be used indiscriminately around long-running network operations. A database transaction that remains open while waiting for an external service can hold locks and consume resources unnecessarily.

## Routing Versus Middleware

Routing and middleware solve different problems.

Routing decides:

`Which handler matches this request?`

Middleware decides:

`What conditions and processing surround this handler?`

Authentication can be implemented as middleware because it applies to many endpoints.

A route parameter such as `/users/:id`, by contrast, belongs to routing because it determines which resource-specific handler receives the request and provides the handler with the extracted identifier.

Putting every backend rule into routing produces an increasingly complicated router. Putting every rule into middleware can hide endpoint-specific behavior. A clear separation keeps each mechanism focused.

## Middleware Versus Handler Logic

Not every validation rule belongs in middleware.

A request body size limit is a cross-cutting transport concern and is suitable for middleware.

Authentication is a reusable access-control boundary and is suitable for middleware.

Whether a new user may use a particular domain role belongs closer to the user-management domain.

Whether a particular user exists belongs to the user repository or endpoint service.

This distinction prevents middleware from becoming a hidden business-logic layer.

## Failure and Edge Cases

Several edge cases are deliberately represented.

A missing route produces `404`.

A known path with an unsupported method produces `405`.

An unauthenticated protected request produces `401`.

An authenticated user without the required role produces `403`.

A missing user resource produces `404` even though the route itself exists.

Malformed JSON produces a client-side parsing failure in the JavaScript and Python server implementations.

Oversized request bodies are rejected before unnecessary application processing.

Invalid user roles are rejected by domain validation.

Malformed or excessively long request IDs are not blindly accepted.

Unexpected exceptions are converted to controlled server errors rather than being returned directly to clients.

## Security Considerations

The examples illustrate security boundaries without pretending that a small demonstration is a complete production security system.

Important backend controls include:

- limit request body sizes
- validate input at trust boundaries
- distinguish authentication from authorization
- avoid returning internal exception details
- avoid storing raw authentication secrets
- use secure credential storage and rotation
- apply security response headers where appropriate
- avoid trusting arbitrary client metadata
- enforce domain invariants at the persistence boundary
- log enough information for correlation without logging secrets

Authorization must be evaluated using the authenticated identity rather than values supplied by the client as ordinary request data.

A client claiming to be an administrator does not establish administrative authority.

## Performance Considerations

Routing performance depends on the number and organization of routes.

A simple linear route scan is adequate for a small service but can become expensive as the route table grows. Production frameworks may use tries, compiled dispatch tables, prefix structures, or optimized method/path maps.

Middleware also has a cost. Each layer adds function calls and usually performs some processing. The cost is generally small for lightweight middleware, but expensive operations such as remote authentication calls, repeated database queries, or synchronous file access can dominate request latency.

Request body limits prevent excessive memory consumption.

Database indexes accelerate common lookups but increase write and storage costs.

Timing should measure meaningful request work without introducing substantial overhead itself.

## Debugging Considerations

Request IDs provide a common correlation key between HTTP responses, application logs, middleware records, and database audit records.

A useful debugging path is:

`request ID -> HTTP request -> route -> middleware execution -> handler outcome -> database operation`

This is more reliable than attempting to reconstruct request behavior from unrelated log timestamps.

`404` debugging should first distinguish an unmatched path from a handler that returned a missing-resource response.

`405` indicates that the path is recognized but the HTTP method is not permitted.

`401` indicates an authentication problem.

`403` indicates that authentication succeeded but authorization failed.

Those distinctions reduce ambiguity during incident investigation.

## Production Design Implications

A production backend typically replaces the demonstration components with a real HTTP runtime, durable persistence, secure credential infrastructure, structured logging, metrics, tracing, configuration management, and deployment controls.

The fundamental architecture remains recognizable:

`HTTP server -> middleware -> router -> application service -> persistence`

The transport implementation can change without requiring the domain model to become responsible for HTTP parsing.

Likewise, the database can change without requiring route definitions to know how SQL statements are executed.

The separation between server, routing, middleware, domain logic, and persistence is the central architectural principle demonstrated throughout these implementations.
