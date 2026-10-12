# HTTP Deep Dive: Methods, Status Codes, Headers, and Cookies

## Scope

This learning set treats HTTP as an application protocol rather than merely a transport used by browsers.

The implementations focus on four closely related areas:

- **Methods** define the intended operation on a target resource.
- **Status codes** communicate the result or state of request processing.
- **Headers** carry protocol metadata that controls representation, caching, authentication, content negotiation, redirects, CORS behavior, and other request or response characteristics.
- **Cookies** provide browser-oriented state management through `Set-Cookie` response fields and `Cookie` request fields.

The important distinction is that these mechanisms operate at different layers of an HTTP exchange. A method describes what the client is asking the server to do. A status code describes what happened while processing that request. Headers provide metadata and control information around the exchange. Cookies are state carried through HTTP headers and interpreted according to cookie-specific delivery rules.

## HTTP Request and Response Model

A simplified exchange has the following structure:

    Client
      |
      |  Method + Target + Request Headers + Optional Body
      v
    HTTP Server
      |
      |  Status + Response Headers + Optional Body
      v
    Client

For example, a resource retrieval may look conceptually like:

    GET /resource/42 HTTP/1.1
    Host: api.example.test
    Accept: application/json
    If-None-Match: "resource-42-v3"

The response can contain:

    HTTP/1.1 200 OK
    Content-Type: application/json
    ETag: "resource-42-v3"
    Cache-Control: private, max-age=60

    {"id":42,"name":"HTTP protocol resource","version":3}

A later request containing the same ETag can receive `304 Not Modified`. In that case the server is telling the client that its cached representation remains valid rather than retransmitting the representation.

## HTTP Methods

Methods are not interchangeable labels. Their semantics influence how clients, intermediaries, caches, APIs, and application code interpret a request.

### GET

`GET` retrieves a representation of a target resource.

The Python, C++, JavaScript, and Java implementations use GET for resource retrieval and show that a successful GET can return representation metadata such as `ETag` and `Cache-Control`.

GET is considered safe because its intended semantics do not request a state-changing operation. Safe does not mean that the server implementation can never perform incidental side effects. Server logging, metrics, authentication activity, and similar operational behavior can still occur.

### HEAD

`HEAD` uses GET-like semantics while omitting the response body.

The Python and JavaScript servers demonstrate HEAD explicitly. The response retains important metadata such as `Content-Type`, `Content-Length`, `ETag`, and caching information while avoiding the representation body.

This makes HEAD useful when a client needs metadata without downloading the complete representation.

### POST

`POST` submits a representation for processing by the target resource.

The examples use JSON request bodies and return `201 Created` when a new resource is successfully accepted.

POST is not generally idempotent. Sending the same POST twice can create two independent resources or trigger the same business operation twice.

The Python, JavaScript, C++, and Java implementations validate `Content-Type` before accepting JSON request bodies.

### PUT

`PUT` is modeled as replacement of a target representation.

The implementations update the complete resource representation and generate a new ETag after the modification.

PUT is idempotent by HTTP semantics. Repeating the same successful PUT should produce the same intended resource state, even though timestamps, logs, metrics, or other incidental effects can change.

### PATCH

`PATCH` represents partial modification.

The implementations treat PATCH separately from PUT so that a partial change does not imply complete replacement.

PATCH is not automatically idempotent. Whether repeated application produces the same state depends on the patch operation itself.

### DELETE

`DELETE` requests removal of the target resource.

The examples return `204 No Content` after deletion.

DELETE is considered idempotent because repeating the intended operation converges on the resource being absent. Idempotence does not require every response to be identical.

### OPTIONS

`OPTIONS` allows a client to discover communication options supported by a target.

The examples use `Allow` to advertise supported methods and include CORS-related fields such as `Access-Control-Allow-Methods` and `Access-Control-Allow-Headers`.

OPTIONS becomes especially important in browser CORS workflows when a browser performs a preflight request before sending a cross-origin request that requires permission.

## Method Properties

Two important properties are demonstrated directly by the Python, C++, and Java implementations.

| Method | Safe | Idempotent | Primary role |
| --- | --- | --- | --- |
| GET | Yes | Yes | Retrieve representation |
| HEAD | Yes | Yes | Retrieve metadata without body |
| POST | No | No | Submit/process data |
| PUT | No | Yes | Replace target representation |
| PATCH | No | Not inherently | Partially modify representation |
| DELETE | No | Yes | Remove target |
| OPTIONS | Yes | Yes | Discover supported communication |

Safe and idempotent are semantic properties. They are not merely programming conventions.

## Status Codes

HTTP status codes are grouped by their first digit.

| Class | Meaning |
| --- | --- |
| 1xx | Informational |
| 2xx | Successful |
| 3xx | Redirection or conditional response |
| 4xx | Client-side request or authorization problem |
| 5xx | Server or upstream service problem |

### 2xx Success

`200 OK` represents a successful operation with a response representation when appropriate.

`201 Created` communicates successful creation and is commonly accompanied by a `Location` header identifying the created resource.

`204 No Content` communicates successful processing without a response body. The DELETE and OPTIONS demonstrations use this status.

`206 Partial Content` is relevant to range retrieval, where a client requests part of a representation rather than the complete representation.

### 3xx Redirection and Conditional Responses

`301 Moved Permanently` represents a permanent redirect.

`302 Found` represents a temporary redirect in the common HTTP API case.

`307 Temporary Redirect` and `308 Permanent Redirect` preserve the request method when redirecting, which makes them distinct from redirect behavior where a client may change how the redirected request is performed.

`304 Not Modified` is not a normal body-bearing success response. It is a cache validation response indicating that the client can reuse an existing representation.

The conditional-request examples use:

    ETag: "resource-v3"

followed by:

    If-None-Match: "resource-v3"

A matching validator produces `304 Not Modified`.

### 4xx Client Errors

`400 Bad Request` is used when the request cannot be processed as a valid request, such as malformed JSON or invalid request metadata in the demonstrations.

`401 Unauthorized` indicates that authentication credentials are required or unacceptable. The examples associate it with `WWW-Authenticate`.

`403 Forbidden` has a different meaning. The server understands the request but refuses to authorize the requested operation.

`404 Not Found` communicates that the target resource is not available.

`405 Method Not Allowed` means the resource exists or is recognized but the requested method is not supported for that target. The `Allow` header can describe permitted methods.

`409 Conflict` is useful when the requested operation conflicts with the current resource state.

`412 Precondition Failed` applies when a request precondition such as an `If-Match` condition is not satisfied.

`415 Unsupported Media Type` is demonstrated when an endpoint expects JSON but receives another representation format.

`422 Unprocessable Content` is used by the examples for syntactically valid input whose semantic content is unacceptable.

`429 Too Many Requests` communicates rate limiting. The examples associate it with `Retry-After`.

### 5xx Server Errors

`500 Internal Server Error` represents an unexpected server-side failure.

`502 Bad Gateway` is associated with a gateway or proxy receiving an invalid response from an upstream service.

`503 Service Unavailable` represents temporary service unavailability and is appropriate for some overloaded or maintenance situations.

`504 Gateway Timeout` represents an upstream timeout observed by a gateway or proxy.

The distinction between 4xx and 5xx is operationally important. A client error generally requires correction of the request, credentials, authorization, or client behavior. A server error generally indicates a problem within the service or an upstream dependency.

## Headers

HTTP headers are metadata fields attached to requests and responses.

Header names are case-insensitive. The Python, C++, and Java implementations explicitly normalize header names for lookup.

### Representation Headers

`Content-Type` identifies the media type of the representation.

The implementations require `application/json` for JSON endpoints.

`Content-Length` communicates the size of a message body in bytes where applicable.

A server should not blindly trust application-level assumptions about body size. The Python and JavaScript examples place explicit limits around body processing.

### Request Metadata

`Host` identifies the target authority in HTTP/1.1 request processing.

`User-Agent` identifies the client software.

`Accept` communicates representations that the client can process.

The JavaScript implementation demonstrates a small content-negotiation routine that chooses JSON or plain text based on `Accept`.

### Authentication Headers

`Authorization` carries credentials or an authorization scheme.

`WWW-Authenticate` is associated with a `401 Unauthorized` response and communicates an authentication challenge.

The examples intentionally distinguish:

    401 Unauthorized

from:

    403 Forbidden

The first indicates an authentication requirement or failure. The second indicates that the server refuses authorization for a request it understands.

### Caching Headers

`Cache-Control` controls caching behavior.

Examples include:

    Cache-Control: private, max-age=60

and:

    Cache-Control: no-store

`ETag` identifies a particular representation version.

`If-None-Match` lets the client ask whether the representation has changed.

The relationship is:

    Server representation
        |
        +--> ETag: "resource-v3"
                  |
                  v
    Client stores representation and validator
                  |
                  v
    If-None-Match: "resource-v3"
                  |
                  v
    Server compares validator
          /                 \
      match              mismatch
        |                    |
      304                  200
        |                    |
    reuse cache        send representation

This mechanism can significantly reduce response-body transfer when resources have not changed.

### Redirect Headers

`Location` identifies the target of a redirect and is also commonly used in a `201 Created` response to identify a newly created resource.

The examples use:

    Location: /resource/43

for a created resource and:

    Location: /resource

for a redirect.

### Allow

`Allow` describes methods supported by a target resource.

The examples return:

    Allow: GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS

for OPTIONS and method-not-allowed scenarios.

### Retry-After

`Retry-After` tells a client how long it should wait before retrying in situations such as rate limiting or temporary unavailability.

The examples use it with `429 Too Many Requests`.

## Cookies

Cookies are state-management fields exchanged through HTTP headers.

A server sends a cookie with:

    Set-Cookie: session_id=...; Path=/; HttpOnly; Secure; SameSite=Lax

The browser later sends the applicable cookie in:

    Cookie: session_id=...

The request does not normally repeat the cookie's attributes. Attributes such as `Secure`, `HttpOnly`, `SameSite`, `Path`, and `Max-Age` are response-side cookie instructions.

### Secure

`Secure` restricts cookie transmission to secure connections.

It is particularly important for session identifiers.

### HttpOnly

`HttpOnly` prevents ordinary browser-side JavaScript from reading the cookie through APIs such as `document.cookie`.

It does not make a session immune to every form of browser compromise. For example, an attacker who can execute malicious JavaScript may still perform authenticated actions through the browser even if the session cookie itself is inaccessible to JavaScript.

### SameSite

`SameSite` controls cross-site cookie behavior.

The examples use `Lax`, which is a common practical setting for many session cookies.

`Strict` applies a stronger cross-site restriction.

`None` permits cross-site cookie use but requires `Secure` in modern browser behavior.

### Path

`Path` restricts the URL path scope for which the browser sends a cookie.

A cookie with `Path=/` is available across the site's paths subject to the other cookie rules.

### Max-Age

`Max-Age` expresses a cookie lifetime in seconds.

Setting a zero lifetime is used by the Java and JavaScript implementations when deleting the demonstration session cookie.

## Session Authentication

The examples use a server-side session model.

The important flow is:

    Login request
        |
        v
    Server creates unpredictable session identifier
        |
        v
    Set-Cookie: session_id=...
        |
        v
    Browser stores cookie
        |
        v
    Later request includes Cookie header
        |
        v
    Server looks up session
        |
        v
    Authenticated application context

The cookie itself is only an identifier. The server-side session record associates that identifier with the authenticated user and expiration time.

Production session systems must protect against session fixation, identifier prediction, theft, replay, excessive lifetime, and improper invalidation.

## Python Implementation

The Python program provides the broadest protocol-oriented simulation.

`HTTPHeaders` demonstrates case-insensitive field lookup and separate storage of header names from normalized lookup keys.

`HTTPRequest` validates the relationship between `Content-Length` and the actual body length. This demonstrates why protocol metadata must be consistent with received data.

The cookie implementation uses Python's `http.cookies.SimpleCookie` rather than manually constructing every cookie field. It demonstrates:

- `Set-Cookie` generation
- `HttpOnly`
- `Secure`
- `SameSite`
- `Path`
- `Max-Age`
- cookie parsing
- cookie deletion

The conditional-request implementation compares an incoming `If-None-Match` value with an ETag and returns either `200` or `304`.

The rate limiter maintains request timestamps per client and produces a retry interval when the configured limit is exceeded.

The built-in `http.server` service connects these concepts into actual executable request handling. Its routes demonstrate GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS, authentication, redirects, cookies, content validation, and conditional requests.

## JavaScript Implementation

The JavaScript program uses Node.js's event-driven HTTP API.

`http.createServer()` exposes the actual request and response streams. Request bodies are processed asynchronously through `data`, `end`, and `error` events.

This is a meaningful JavaScript-specific distinction from the Python program. Node does not require a blocking request-body read. The body arrives through an event-driven stream.

The implementation uses:

- `IncomingMessage.headers` for normalized incoming header access
- `ServerResponse.writeHead()` for response status and headers
- Promises around asynchronous request-body collection
- `URL` for request-target parsing
- `crypto.randomBytes()` for session identifiers
- `crypto.randomUUID()` for request tracing
- explicit `Set-Cookie` serialization
- conditional ETag processing
- OPTIONS handling
- CORS response metadata
- redirects
- content negotiation

The JavaScript cookie parser also demonstrates that multiple cookies arrive as one `Cookie` request field separated by semicolons, while a server emits cookies using `Set-Cookie`.

## C++ Case Study

The C++ program models an HTTP gateway rather than implementing raw socket parsing.

This separation is deliberate. The important technical problem is the protocol state and policy, not reproducing an entire TCP and HTTP parser.

`HttpMethod` represents method semantics as an enum instead of treating methods as arbitrary strings. The enum provides explicit safe and idempotent properties.

`StatusCode` separates numeric status representation from human-readable reason phrases.

`Headers` implements case-insensitive header lookup. This matters because HTTP field names are case-insensitive.

`HttpGateway` coordinates resource processing, conditional requests, authentication, cookies, and rate limiting.

The resource model maintains an ETag that changes whenever the resource version changes. A request carrying the matching `If-None-Match` value receives `304 Not Modified`.

The cookie model represents attributes explicitly. This prevents the common mistake of treating a cookie as only a `name=value` pair when security behavior is actually controlled by additional attributes.

`RateLimiter` demonstrates protocol-level throttling that produces `429 Too Many Requests` rather than allowing unlimited request processing.

The case study therefore represents HTTP as a collection of interacting state machines rather than isolated status codes.

## Java Enterprise Model

The Java implementation emphasizes explicit domain types and service boundaries.

`HttpMethod`, `Status`, `HttpRequest`, `HttpResponse`, `Resource`, `Session`, and `Cookie` represent different protocol concepts.

The implementation does not collapse the entire HTTP exchange into one unstructured map. Headers are managed separately because they have protocol-specific case-insensitive names and values.

`ResourceService` owns resource state transitions. PUT and PATCH call different service methods, preserving their semantic distinction.

`SessionService` owns authentication state. It creates session identifiers, tracks expiration, authenticates incoming cookie values, and removes sessions during logout.

`RateLimiter` applies request-frequency policy independently of resource processing.

`HttpService` acts as the application-level HTTP coordinator. It translates protocol conditions into appropriate response statuses such as `401`, `404`, `405`, `415`, `422`, `429`, and `304`.

The use of records makes immutable value-oriented protocol objects convenient, while mutable service state remains contained in dedicated service classes.

## SQL Data Model

The SQL implementation models HTTP observations relationally.

`repositories` identifies the API or service context.

`http_resources` stores target resources and their current ETags.

`clients` records client identities and user-agent information.

`users` and `sessions` represent authenticated server-side session state.

`cookies` records cookie metadata including security attributes.

`http_exchanges` represents request and response activity.

`request_headers` and `response_headers` normalize header data away from the main exchange table. This makes it possible to query individual fields such as `If-None-Match`, `ETag`, `Cache-Control`, `Content-Type`, `Location`, and `Retry-After`.

`status_codes` provides a reference table for status classification.

`allowed_resource_methods` represents method policy for resources.

`rate_limit_events` records throttling decisions independently of the exchange itself.

The schema uses foreign keys to preserve relationships between exchanges, resources, clients, users, sessions, and headers.

## Database-Level Validation

The cookie table contains a direct constraint:

    CHECK (
        same_site <> 'None'
        OR secure = TRUE
    )

This expresses an important cookie-security relationship at the database layer.

The trigger `cookie_security_validation` reinforces cookie validation before insertion or update.

Status codes are constrained to the valid HTTP range.

Resource paths must begin with `/`.

Session expiration must occur after session creation.

These constraints demonstrate why protocol-related data quality should not depend entirely on application code.

## SQL Queries and Protocol Analysis

The SQL views provide operational analysis rather than merely storing records.

`http_exchange_analysis` joins exchange records with clients and calculates a status class and latency.

Queries can identify:

- client-error responses
- conditional requests
- ETag behavior
- secure and HttpOnly cookies
- expired or revoked sessions
- allowed resource methods
- average and maximum response latency
- rate-limited requests

The result is a relational representation of the same protocol concepts modeled by the application implementations, but SQL approaches them through constraints, relationships, aggregation, indexing, and transactional operations.

## Relationships Between the Four Core Areas

The four main areas should not be treated as synonyms.

A method answers:

> What operation is being requested?

A status code answers:

> What was the result of processing the request?

Headers answer:

> What metadata and protocol controls accompany this exchange?

Cookies answer:

> What browser-managed state should be persisted and returned on applicable requests?

A single exchange can involve all four.

For example:

    POST /login
    Content-Type: application/json

can produce:

    200 OK
    Set-Cookie: session_id=...; HttpOnly; Secure; SameSite=Lax

The method is POST because the client is submitting login information. The status is 200 because the operation succeeded. `Content-Type` describes the submitted representation. `Set-Cookie` establishes authenticated browser state.

A later request can be:

    GET /me
    Cookie: session_id=...

with:

    200 OK
    Content-Type: application/json

The method retrieves the authenticated representation. The cookie supplies session state. The response status communicates success.

## Conditional Requests

Conditional requests connect headers and status codes directly.

A server first returns:

    ETag: "resource-v3"

The client can store the representation and validator.

On a later request:

    If-None-Match: "resource-v3"

The server compares the validator with its current representation.

If the representation is unchanged:

    304 Not Modified

The client reuses its stored representation.

If the representation has changed:

    200 OK
    ETag: "resource-v4"

The new representation is transferred.

This is different from returning `200` with an unchanged body every time because the conditional response can avoid transferring the representation.

## Authentication Versus Authorization

The examples intentionally distinguish authentication-related status behavior.

Authentication answers:

> Who is making the request?

Authorization answers:

> Is that authenticated principal permitted to perform this operation?

`401 Unauthorized` is associated with an authentication challenge.

`403 Forbidden` indicates that the server refuses the operation despite understanding the request.

This distinction matters for API clients, security logging, troubleshooting, and access-control design.

## Content-Type and Accept

`Content-Type` describes the representation being sent.

For example:

    Content-Type: application/json

means that the request body is JSON.

`Accept` communicates which representations the client is willing to receive.

For example:

    Accept: application/json, text/plain

The JavaScript and Python implementations demonstrate server-side selection between supported response formats.

These headers operate in opposite directions:

| Header | Describes |
| --- | --- |
| `Content-Type` | Representation actually being sent |
| `Accept` | Representation the client wants to receive |

Confusing these fields can produce incorrect API behavior and inappropriate `415` or `406` responses.

## CORS and OPTIONS

Browser cross-origin requests can require an OPTIONS preflight.

A server may return:

    Access-Control-Allow-Methods: GET, POST, PUT, PATCH
    Access-Control-Allow-Headers: Content-Type, Authorization
    Access-Control-Max-Age: 600

The purpose is to communicate which cross-origin request characteristics the browser may proceed with.

CORS is not an authentication mechanism and does not replace server-side authorization.

The JavaScript and Java implementations demonstrate OPTIONS processing independently from normal resource operations.

## Common Protocol Mistakes

### Treating all 4xx responses as equivalent

`400`, `401`, `403`, `404`, `405`, `409`, `412`, `415`, `422`, and `429` communicate different conditions.

A client that treats every 4xx response as the same loses useful protocol information and makes recovery behavior less precise.

### Using 200 for every outcome

Returning `200 OK` for validation failures, authentication failures, missing resources, and rate limiting makes API behavior harder for clients and monitoring systems to interpret.

The implementations use meaningful status codes instead.

### Confusing PUT and PATCH

PUT models replacement semantics. PATCH models partial modification.

The examples intentionally keep their service operations separate.

### Ignoring Content-Type

An API that expects JSON should validate the representation type rather than assuming that every body contains JSON.

The implementations return `415 Unsupported Media Type` when the declared media type is not supported.

### Treating cookies as authentication by themselves

A cookie is a delivery mechanism for state. A session cookie normally contains an identifier that must be associated with server-side authentication state.

The server must validate the identifier, expiration, revocation state, and authorization context.

### Omitting cookie security attributes

Session cookies should be evaluated for `Secure`, `HttpOnly`, `SameSite`, appropriate `Path`, and an appropriate lifetime.

The correct configuration depends on the application architecture and browser interaction requirements.

### Treating headers as case-sensitive

HTTP field names are case-insensitive. The Python, C++, and Java implementations explicitly account for this.

### Ignoring request-body limits

Request bodies can consume memory and processing resources. The Python and JavaScript implementations impose size limits rather than reading unbounded data.

## Performance Considerations

ETags can reduce response-body transfer when resources are unchanged.

`Cache-Control` can reduce repeated origin requests when an appropriate cache policy is possible.

Indexes on request paths, methods, status codes, timestamps, and header names allow the SQL implementation to analyze HTTP activity efficiently.

The JavaScript implementation processes request bodies asynchronously because Node.js is built around an event-driven I/O model.

The C++ implementation uses direct value-oriented structures and hash maps for resource, session, and rate-limit state.

The Java implementation separates resource, session, and rate-limit services so that each state-management responsibility can evolve independently.

## Security Considerations

HTTP security cannot be reduced to one header.

Important areas represented by these implementations include:

- session identifier unpredictability
- session expiration and revocation
- `HttpOnly` cookies
- `Secure` cookies
- `SameSite` policy
- content-type validation
- request-body size limits
- rate limiting
- authentication challenges
- authorization decisions
- conditional request handling
- careful header processing
- avoidance of unsafe header construction from untrusted values

The cookie demonstrations use explicit validation for the relationship between `SameSite=None` and `Secure`.

The server implementations also avoid treating arbitrary request data as trusted JSON or unrestricted body content.

## Debugging HTTP Exchanges

A useful debugging process follows the complete exchange rather than looking only at the final status.

Inspect:

    Method
    Request target
    Request headers
    Request body
    Response status
    Response headers
    Response body

For authentication problems, inspect both:

    Cookie
    Set-Cookie

For cache-validation problems, inspect both:

    ETag
    If-None-Match

For content errors, inspect:

    Content-Type
    Accept
    Response status

For rate limiting, inspect:

    429
    Retry-After

For method errors, inspect:

    405
    Allow

This approach preserves the relationship between the protocol fields instead of treating each field as an isolated value.

## Production Design Implications

A production HTTP service should maintain a clear separation between protocol processing and application-domain behavior.

HTTP routing determines the target operation.

Validation determines whether the request can be processed.

Authentication establishes the caller identity.

Authorization determines whether the requested operation is permitted.

Application logic performs the requested business operation.

The HTTP layer then maps the result to an appropriate status code, headers, cookies, and representation.

That separation makes protocol behavior easier to test and prevents business logic from becoming tightly coupled to raw HTTP details.

The five implementations demonstrate the same protocol through different technical perspectives: Python emphasizes executable protocol simulation and a local server, JavaScript emphasizes event-driven HTTP streams, C++ models a gateway and protocol state explicitly, Java models enterprise service boundaries and domain types, and PostgreSQL represents the exchange as constrained relational data.
