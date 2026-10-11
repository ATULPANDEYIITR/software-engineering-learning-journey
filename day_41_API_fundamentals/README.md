# API Fundamentals: REST, Resources, Endpoints, and HTTP

## Scope

This learning set models a small resource-oriented API across Python, JavaScript, C++, Java, and PostgreSQL. The central distinction is between the **resource**, its **URI**, the **endpoint operation**, and the **HTTP protocol message** used to interact with it.

A REST API does not make a resource equivalent to an endpoint. A resource is a domain object or collection that can be identified by a URI. An endpoint is an addressable API interface, commonly understood as a URI or URI template together with an HTTP method and its contract. HTTP supplies the standardized request and response semantics used to transfer representations of those resources.

The implementations use a common domain of operational resources while deliberately approaching the problem differently in each language.

## Core Model

A useful conceptual model is:

`HTTP request -> endpoint matching -> resource operation -> representation -> HTTP response`

For example:

`GET /api/v1/resources/42`

identifies resource `42` through its URI and requests its current representation with the HTTP `GET` method.

The collection URI:

`/api/v1/resources`

represents the resource collection.

The member URI:

`/api/v1/resources/42`

identifies one member of that collection.

The distinction matters because the same resource URI can support several HTTP methods with different semantics.

| HTTP method | Typical API purpose | Resource effect |
|---|---|---|
| `GET` | Retrieve a representation | Should not modify the resource |
| `POST` | Create subordinate resource or trigger collection-oriented processing | Usually creates a new resource |
| `PUT` | Replace a resource representation | Replaces the addressed representation |
| `PATCH` | Apply a partial modification | Changes selected representation fields |
| `DELETE` | Remove the addressed resource | Deletes the resource |
| `HEAD` | Retrieve response metadata without a response body | Does not modify the resource |

The API examples use JSON representations because JSON is a common interchange format for REST APIs. REST itself does not require JSON.

## Resources

A resource represents something meaningful in the API's domain. In these implementations, a resource contains:

- A stable identifier.
- A human-readable name.
- A category.
- A lifecycle status.
- A representation version.
- Creation and modification timestamps.

The identifier is important because resource identity should not depend on mutable attributes such as a display name.

Changing a resource from `active` to `maintenance` should not change its URI. The same resource remains identifiable through its original member URI while its representation changes.

The Python implementation represents this domain with the `Resource` dataclass and protects its collection through `ResourceStore`. The Java implementation uses an immutable-style `record` and a repository abstraction. The C++ case study separates domain resources from HTTP request processing. The SQL implementation stores resource identity and state with database constraints.

## REST Collections and Member Resources

The collection endpoint:

`/api/v1/resources`

has collection semantics.

A `GET` against it retrieves a representation containing multiple resources. A `POST` against it requests creation of a new member.

The member endpoint:

`/api/v1/resources/{id}`

has individual-resource semantics.

A `GET` retrieves one member. `PUT` replaces its representation. `PATCH` changes part of it. `DELETE` removes it.

This distinction prevents an API from becoming a collection of unrelated command URLs such as `/createResource`, `/updateResource`, and `/deleteResource`. The resource-oriented design uses stable resource identifiers while HTTP methods communicate the requested operation.

## Endpoints

An endpoint is defined by more than a path string.

For these examples, an endpoint is effectively described by:

`HTTP method + URI pattern + request representation + response representation + status behavior`

Consequently:

`GET /api/v1/resources/7`

and:

`DELETE /api/v1/resources/7`

refer to the same member URI but represent different endpoint operations.

The Python router uses regular expressions to distinguish the collection endpoint from a member endpoint. The JavaScript server uses Node's URL parsing and route matching. The C++ implementation explicitly separates endpoint parsing from domain services. The Java implementation uses an endpoint service that translates URI and method combinations into domain operations.

The SQL model stores endpoint definitions explicitly so the API contract can be queried and analyzed as data.

## HTTP Requests

An HTTP request has a method, target URI, headers, and, when appropriate, a representation body.

A simplified request is conceptually:

`POST /api/v1/resources`

with:

`Content-Type: application/json`

and a JSON representation containing the new resource fields.

Headers carry protocol metadata rather than being mixed into the JSON domain representation.

Important headers demonstrated by the implementations include:

- `Content-Type` identifies the media type of a request or response representation.
- `Accept` communicates preferred response media types.
- `Location` identifies the URI of a newly created resource.
- `ETag` identifies a particular representation version.
- `If-None-Match` enables conditional retrieval.

The Python and JavaScript servers reject JSON bodies when the request does not identify an appropriate JSON content type. This makes the representation contract explicit.

## HTTP Responses

HTTP status codes communicate the broad outcome of an operation.

The implementations use several important statuses:

| Status | Meaning in the API |
|---|---|
| `200 OK` | Request succeeded and a representation is returned |
| `201 Created` | A new resource was created |
| `204 No Content` | Operation succeeded without a response representation |
| `304 Not Modified` | Conditional retrieval found no changed representation |
| `400 Bad Request` | Request syntax or structure is invalid |
| `404 Not Found` | Requested resource or endpoint does not exist |
| `405 Method Not Allowed` | URI exists but the requested HTTP method is not supported there |
| `413 Request Entity Too Large` | Request body exceeds the server's configured limit |
| `415 Unsupported Media Type` | Representation media type is not accepted |
| `422 Unprocessable Entity` | Request structure is valid but domain validation fails |

A JSON error body can provide additional detail, but it should not replace the HTTP status code.

For example, a missing resource should not return `200` with an object such as `{"error":"not found"}`. The HTTP response should communicate the failure with `404`.

## REST Representations

A resource and its representation are related but not identical.

The resource is the conceptual domain object. A representation is the serialized form transferred over HTTP.

The examples use JSON representations such as:

`{"id":2,"name":"Order API","category":"application","status":"active"}`

The Python implementation converts resource objects into JSON through the standard library. The JavaScript implementation uses `JSON.stringify`. The C++ program constructs a JSON representation at its protocol boundary. Java exposes representation maps. PostgreSQL stores the underlying relational state rather than treating JSON as the primary domain model.

This distinction allows an API to evolve its representation without changing the fundamental identity of the resource.

## HTTP Method Semantics

### GET

`GET` retrieves a representation.

The implementations treat `GET` as non-mutating. Retrieving a resource should not increment its domain version or change its state.

A collection `GET` can support filtering and pagination:

`GET /api/v1/resources?category=application&limit=20&offset=0`

The query parameters refine the representation being requested. They do not create new resource identities.

### POST

`POST` is used on the collection endpoint to create a new member.

A successful creation returns `201 Created` and a `Location` header such as:

`Location: /api/v1/resources/8`

The new URI tells the client where the created resource can subsequently be retrieved.

### PUT

`PUT` addresses a particular resource and represents replacement semantics.

The Python and C++ implementations distinguish replacement from partial modification. A replacement request supplies the representation required for the complete resource state.

A practical API must define clearly whether omitted properties are rejected, reset, or interpreted in some other contract-specific way.

### PATCH

`PATCH` is intended for partial modification.

The examples use a status change to demonstrate why `PATCH` is distinct from `PUT`. A request can change `active` to `maintenance` without reconstructing every resource property.

Real APIs should define their patch format precisely. A simplistic field merge is not equivalent to every standardized PATCH representation.

### DELETE

`DELETE` removes the addressed resource.

The successful example returns `204 No Content`. A subsequent `GET` would then produce `404` for a resource that no longer exists.

Deletion semantics can vary in production systems. Some domains use soft deletion or archival because regulatory, audit, or recovery requirements make physical deletion inappropriate.

### HEAD

`HEAD` is useful when the client needs response metadata without transferring the representation body.

The examples expose the resource's `ETag` through `HEAD`. This can be useful for cache validation and metadata inspection.

## Endpoint Matching

Endpoint matching is the mechanism that connects a request URI to application behavior.

The Python implementation separates collection and member routes with regular expressions.

The JavaScript implementation uses `URL` parsing and path matching.

The C++ case study uses `EndpointParser` to identify collection and member forms before the API layer invokes domain services.

The Java implementation centralizes dispatch in `RestEndpointService`.

This separation is important because URI parsing should not be mixed deeply into resource persistence logic. The database should not be responsible for deciding whether `/api/v1/resources/abc` matches a member route. The API boundary should resolve the request first.

## Validation

Validation occurs at multiple boundaries.

HTTP-level validation concerns whether a request can be interpreted correctly. Examples include malformed JSON and an inappropriate `Content-Type`.

Domain-level validation concerns whether the requested resource state is valid. The examples reject blank names, oversized names, empty categories, and unsupported status values.

Database validation provides a final integrity boundary. The PostgreSQL script uses `NOT NULL`, `CHECK`, `UNIQUE`, enum, primary-key, and foreign-key constraints.

The layers solve different problems. Application validation can produce precise client errors, while database constraints protect stored data even when another client bypasses the normal application path.

## Conditional Requests and ETags

The implementations demonstrate `ETag` and `If-None-Match`.

An ETag identifies a particular representation version. For example:

`ETag: "resource-2-version-3"`

A client can later send:

`If-None-Match: "resource-2-version-3"`

If the representation is unchanged, the server can return:

`304 Not Modified`

without sending the complete representation again.

The Python and JavaScript implementations calculate ETags from resource version information. The C++ implementation uses the resource identifier and version. The Java implementation creates an ETag from the same domain concepts.

ETags are especially useful for reducing repeated representation transfer and detecting representation changes.

## Pagination and Collection Representations

Large collections should not normally be returned without bounds.

The Python and JavaScript APIs accept `limit` and `offset`. The SQL implementation uses `LIMIT` and `OFFSET` for collection queries.

A collection response contains both data and pagination metadata:

`data` contains the selected resource representations.

`pagination.total` indicates the total matching resource count.

`pagination.limit` identifies the requested page size.

`pagination.offset` identifies the starting position.

Production APIs may use cursor-based pagination when datasets are large or frequently changing because offset pagination can become expensive and can produce unstable pages when records are inserted or deleted between requests.

## Python Implementation

The Python program implements an actual HTTP server using `http.server` and `ThreadingHTTPServer`.

`ResourceStore` owns resource state and validation. `ApiRouter` maps HTTP requests to resource operations. `RestHandler` handles the HTTP transport boundary.

The implementation demonstrates:

- Collection and member URI routing.
- JSON request parsing.
- Content-Type validation.
- Request body size limits.
- GET, POST, PUT, PATCH, DELETE, and HEAD.
- HTTP status handling.
- `Location` on creation.
- ETag generation.
- Conditional GET.
- Query-based filtering.
- Pagination.
- Thread-safe in-memory resource access.
- Structured error responses.

The server uses a lock around mutable resource operations because `ThreadingHTTPServer` can process requests concurrently. This makes the example materially different from a single-threaded dictionary tutorial.

The script also launches an HTTP client against itself. This demonstrates the complete request-response cycle instead of merely calling application functions directly.

## JavaScript Implementation

The JavaScript program uses Node's built-in `http` module.

Its main technical distinction is the event-driven request model. Request-body processing is asynchronous because the body arrives through stream events. The client demonstration also uses promises around Node's HTTP client.

`ResourceRepository` stores resources, while route handling remains at the HTTP boundary.

The JavaScript implementation demonstrates:

- Node HTTP server behavior.
- URL parsing.
- Asynchronous request-body collection.
- Request size enforcement.
- JSON parsing.
- REST route matching.
- HTTP status responses.
- ETag generation with Node's `crypto` module.
- Conditional requests.
- Collection pagination.
- PUT versus PATCH behavior.
- Promise-based HTTP client calls.
- Server shutdown after the demonstration completes.

This is not simply a Python translation. It demonstrates why asynchronous stream handling is an important part of HTTP programming in Node.js.

## C++ Case Study

The C++ implementation models an operational resource API without requiring an external HTTP library.

`ResourceService` is responsible for domain operations. `EndpointParser` determines whether a URI represents a collection or member resource. `RestApi` translates HTTP-like requests into service operations.

The separation demonstrates an important architecture boundary:

`HTTP representation -> API routing -> domain service -> resource state`

The case study uses `unordered_map` for resource lookup by identifier, giving average constant-time lookup under normal hash-table behavior.

A vector is used when a collection representation is assembled. The result is sorted by resource identifier so output remains deterministic.

The C++ program also models conditional retrieval through ETags. The ETag is tied to the resource identifier and representation version rather than to mutable display data alone.

Error handling uses a domain-specific exception carrying an HTTP status. This prevents every service method from manually constructing HTTP responses.

## Java Implementation

The Java program uses an enterprise-oriented separation between repository, service, validation, representation, and endpoint layers.

The `ResourceRepository` interface defines persistence behavior independently from the in-memory implementation. This makes the domain service independent of the specific storage mechanism.

The `Resource` record provides a compact immutable representation of domain state. Rather than mutating the record, replacement creates a new version.

`ResourceValidator` centralizes domain validation.

`ResourceService` owns business operations such as creation, retrieval, status modification, replacement, and deletion.

`RestEndpointService` is responsible for translating endpoint and HTTP method semantics into service calls.

The Java program therefore demonstrates a layered API design rather than a controller filled with persistence logic.

The `AtomicInteger` identifier sequence illustrates safe identifier generation when operations may originate from concurrent execution. A production persistence layer would normally delegate durable identifier generation to the database.

## PostgreSQL Data Model

The SQL implementation treats API behavior as a relational domain.

`resources` stores actual REST resources.

`endpoints` stores the supported endpoint contract.

`api_clients` identifies clients making requests.

`http_requests` records method, path, endpoint, resource, media-type, and conditional-request information.

`api_responses` stores HTTP status, ETag, Location, content type, and response time.

`resource_change_log` records resource version transitions.

The foreign keys connect HTTP activity to known clients, endpoints, and resources.

The `resources` table uses an enum for lifecycle status. This prevents arbitrary strings such as `deleted-but-not-really` from entering a column that only permits known states.

The unique resource-name constraint provides an example of a domain invariant enforced by PostgreSQL rather than application code alone.

## Database Constraints and API Integrity

API validation should not be treated as a replacement for database integrity.

For example, the application can reject an empty resource name before an `INSERT`, but the database still protects itself with:

`CHECK (length(trim(name)) > 0)`

The resource identifier is protected by the primary key.

Endpoint uniqueness is protected by:

`UNIQUE (path_template, method)`

This matters because the combination of URI template and method defines a distinct endpoint operation in the model.

Foreign keys prevent request records from referencing nonexistent clients or endpoint definitions.

The database therefore provides a second line of defense against invalid state.

## Transactions

The SQL script uses transactions when resource changes and audit entries are logically one operation.

A resource update is followed by an entry in `resource_change_log` inside the same transaction.

If the transaction fails before `COMMIT`, neither the resource update nor its audit entry should become durable.

This is important for API systems where audit history is part of operational correctness rather than optional logging.

## Error Boundaries

There are several distinct failure classes.

A malformed JSON body is a protocol representation problem.

An unsupported media type is a representation negotiation problem.

A nonexistent URI is an endpoint resolution problem.

A nonexistent resource is a resource identity problem.

An invalid status value is a domain validation problem.

A database constraint violation is a persistence integrity problem.

Separating these categories produces more useful HTTP behavior and clearer diagnostics than returning the same generic error for every failure.

## Common API Design Mistakes

Treating every path as an independent command endpoint makes resource identity difficult to reason about. The examples instead use stable collection and member resources.

Returning `200 OK` for every outcome hides important protocol semantics. Status codes should communicate success, creation, absence, invalid requests, and unsupported methods.

Putting mutable state into the URI can create unstable identities. A resource identifier should remain stable while its representation changes.

Accepting unlimited request bodies creates an avoidable resource-exhaustion risk. The Python and JavaScript examples impose a request-size limit.

Trusting arbitrary client input without validation allows invalid domain state to reach the application or database.

Returning internal exception details in production error responses can disclose implementation information. The examples expose controlled messages rather than stack traces.

Ignoring conditional requests can cause unnecessary representation transfers for clients that repeatedly request unchanged resources.

## Security Considerations

HTTP APIs should treat all client input as untrusted.

The examples validate path identifiers, query parameters, request bodies, content types, and allowed status values.

A production API would also need authentication and authorization. Authentication establishes who is making the request; authorization determines whether that caller may perform the requested operation.

TLS should protect HTTP traffic in production. Sensitive credentials and tokens should not be transmitted over unencrypted HTTP.

Request size limits help reduce resource-exhaustion attacks.

Error responses should avoid exposing stack traces, SQL statements, internal filesystem paths, secrets, or infrastructure details.

Database constraints remain valuable even when an API performs application-level authorization and validation because multiple services or maintenance processes may interact with the same database.

## Performance Considerations

Resource lookup by identifier should normally be indexed. The in-memory implementations use maps for direct lookup, while PostgreSQL uses the primary key index.

Category filtering has an explicit PostgreSQL index because collection queries frequently filter by category.

Request history is indexed by resource and request time to support recent-activity analysis.

Pagination limits the amount of collection data returned by one request.

ETags can reduce repeated response transfer when representations have not changed.

The correct pagination strategy depends on workload. Offset pagination is easy to understand but can become expensive for large offsets. Cursor-based pagination is often more appropriate for high-volume collections.

## Relationship Between REST, Resources, Endpoints, and HTTP

These concepts should remain distinct:

**REST** is the architectural style guiding resource-oriented interaction.

**A resource** is a conceptual domain object or collection that can be identified.

**A URI** identifies that resource.

**An endpoint** defines how an API exposes an addressable operation through a URI and HTTP method.

**HTTP** supplies the protocol semantics for requests, responses, methods, headers, representations, and status codes.

The practical flow is therefore not simply "REST equals HTTP endpoint." A REST-oriented API uses HTTP as a protocol to expose representations of resources through well-defined resource identifiers and method semantics.

## Practical Architecture

The six artifacts collectively represent a layered API architecture:

`Client`

↓

`HTTP request`

↓

`Endpoint and URI routing`

↓

`Representation validation`

↓

`Domain service`

↓

`Resource state`

↓

`Database persistence`

↓

`HTTP response`

The Python and JavaScript implementations emphasize executable HTTP behavior.

The C++ implementation emphasizes separation between protocol routing and domain services.

The Java implementation emphasizes explicit enterprise domain abstractions and repository boundaries.

The SQL implementation emphasizes durable resource state, relational relationships, integrity constraints, audit history, and API activity analysis.

These perspectives are complementary because API fundamentals involve both protocol semantics and the software architecture required to implement them reliably.
