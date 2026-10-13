# REST API Design: URI Design, Versioning, and Pagination

## Scope

This learning artifact treats REST API design as a resource-oriented contract rather than as a collection of HTTP endpoints.

The three central areas are deliberately separated:

- **URI design** defines how resources and collections are represented as stable addresses.
- **API versioning** defines how incompatible contract evolution is exposed without silently changing the meaning of an existing contract.
- **Pagination** defines how large collections are represented across multiple responses without requiring a client to retrieve an unbounded result set.

The implementations model these concerns at different architectural levels. Python provides an executable HTTP API. JavaScript builds an event-driven Node.js implementation. C++ models an API governance and policy engine beneath an HTTP transport. Java represents the same problem through explicit enterprise domain types and validation services. PostgreSQL stores the durable governance model and enforces structural constraints.

---

## Resource-Oriented URI Design

A resource-oriented API identifies nouns rather than operations.

A collection URI such as `/api/v1/books` represents a collection of book resources. An individual URI such as `/api/v1/books/42` identifies one member of that collection.

This distinction makes HTTP methods meaningful:

| URI | HTTP method | Resource meaning |
| --- | --- | --- |
| `/api/v1/books` | `GET` | Retrieve a representation of the collection |
| `/api/v1/books` | `POST` | Create a new member of the collection |
| `/api/v1/books/42` | `GET` | Retrieve book 42 |
| `/api/v1/books/42` | `PATCH` | Partially modify book 42 |
| `/api/v1/books/42` | `DELETE` | Remove book 42 |

An action-oriented URI such as `/api/v1/getBooks` mixes the operation into the address. The resource-oriented form leaves the operation to HTTP and lets the URI identify the thing being operated on.

A collection and an individual resource are different representations of the resource model. `/books` is not merely `/books/` with an optional identifier. The collection has its own semantics, while `/books/42` identifies a particular member.

---

## URI Parameters and Query Parameters

Path parameters identify a resource.

`/api/v1/books/42`

Here `42` identifies the book.

Query parameters modify retrieval of a collection or representation without changing the identity of the collection.

`/api/v1/books?category=api-design`

The URI still represents the books collection. The query expresses a retrieval constraint.

Pagination is another retrieval concern:

`/api/v1/books?page=2&page_size=20`

Filtering and pagination can be combined:

`/api/v1/books?category=api-design&page=2&page_size=20`

The Python and JavaScript implementations parse these parameters explicitly and reject malformed values instead of silently falling back to potentially dangerous defaults.

---

## Stable URI Naming

The implementations use plural collection names:

`/api/v1/books`

and:

`/api/v1/orders`

This convention communicates that the URI represents a collection.

A resource hierarchy can represent a genuine containment relationship. For example:

`/api/v1/customers/17/orders`

can represent orders associated with customer 17 when that relationship is central to the API's resource model.

Deeply nested URIs should not be introduced merely because a database has several foreign keys. A relational relationship does not automatically require a hierarchical URI.

The URI should communicate a useful resource relationship, not expose the internal database schema.

---

## API Versioning

The examples use URI-based major versioning:

`/api/v1/books`

The version is part of the contract namespace.

The implementations distinguish three lifecycle states:

| State | Meaning | Typical behavior |
| --- | --- | --- |
| Active | Current supported contract | Normal requests are accepted |
| Deprecated | Still available but scheduled for migration | Requests can succeed while carrying migration information |
| Retired | Contract is no longer served | Requests receive `410 Gone` |

The C++ and Java policy engines explicitly model these states. The SQL schema persists them as an enumerated database type.

Versioning is primarily valuable when an API change alters the meaning or shape of an existing contract.

A compatible addition may not require a new major version. An incompatible change such as changing the meaning of a field, removing a required field, changing resource semantics, or changing response structure can require a separate contract.

The important property is that clients using the existing contract should not unexpectedly receive a representation whose meaning has changed.

---

## Version Lifecycle

A version should have an explicit lifecycle rather than disappearing without notice.

The SQL model stores:

- version identifier
- lifecycle state
- release date
- sunset date

The Java and C++ implementations reproduce the same lifecycle at the domain-policy level.

A deprecated version can remain operational:

`GET /api/v2/books`

while the server communicates that clients should migrate.

A retired version is treated differently:

`GET /api/v0/books`

returns a `410 Gone` decision in the policy models.

The distinction between `404 Not Found` and `410 Gone` is meaningful. A nonexistent resource or unsupported URI can produce `404`. A known resource or API contract that has intentionally been removed can be represented by `410`.

---

## URI Versioning Versus Header Versioning

URI versioning is explicit:

`/api/v1/books`

A client can see the contract version directly in logs, traces, browser requests, gateway rules, and documentation.

Another design is media-type or header-based versioning, where the URI remains stable and the requested representation is selected through HTTP headers.

For example, a representation could be negotiated through an `Accept` header.

The implementations in this artifact intentionally use URI versioning because it makes routing and lifecycle behavior directly visible. The choice is architectural rather than a claim that URI versioning is universally superior.

A production system should select one consistent strategy and apply it systematically rather than mixing incompatible version-selection rules across resources.

---

## Pagination

Returning every member of a large collection in one response creates several problems:

- response size becomes unpredictable;
- database work can become expensive;
- serialization consumes more CPU and memory;
- network transfer takes longer;
- clients must process potentially huge representations;
- repeated requests can amplify infrastructure load.

Pagination bounds the amount of collection data represented by a single response.

The Python, JavaScript, and Java examples implement page-size validation. The SQL schema stores pagination policies as durable configuration.

---

## Page-Number Pagination

The page-number form is represented as:

`/api/v1/books?page=2&page_size=20`

A simple calculation is:

`offset = (page - 1) × page_size`

For page 2 with a page size of 20:

`offset = 20`

Page-number pagination is straightforward for administrative interfaces and relatively stable collections.

It has an important limitation for frequently changing datasets. If records are inserted or deleted between requests, the contents of a later page can shift. A client may observe duplicates or skip records because the offset refers to a moving position.

Stable ordering is therefore essential.

The Python and JavaScript implementations sort books by ID before slicing the collection. This makes the demonstration deterministic.

---

## Pagination Metadata

The Python implementation returns metadata containing:

- current page;
- page size;
- total number of items;
- total number of pages;
- whether a previous page exists;
- whether a next page exists.

It also generates links for:

- current page;
- first page;
- previous page when available;
- next page when available;
- last page when a result set exists.

A representative response structure is conceptually:

`data`

containing the resources,

`pagination`

containing collection state,

and

`links`

containing navigation information.

The actual Python implementation generates this structure programmatically rather than merely printing a documentation example.

---

## Page-Size Limits

The implementations enforce a maximum page size.

The Python and JavaScript servers reject a page size greater than 50.

The C++ policy engine uses a maximum of 100 for its independent policy model.

The Java policy registry also defines a maximum of 100.

The SQL database stores maximum page sizes in `pagination_policies`.

A page-size limit is a resource-protection mechanism. Without a limit, a request such as:

`/api/v1/books?page=1&page_size=100000000`

could turn a normal collection request into an expensive database and serialization operation.

A maximum should be selected according to the resource size, database behavior, response latency objectives, and client needs.

---

## Cursor Pagination

The C++ and Java implementations explicitly distinguish page-number pagination from cursor pagination.

A cursor-based request can look conceptually like:

`/api/v1/orders?cursor=eyJpZCI6MTAw`

The cursor represents a position in the ordered result stream rather than an absolute page number.

Cursor pagination is useful for large, frequently changing collections because it can avoid the large offsets associated with deep page-number pagination.

A cursor must be treated as opaque by the client. Clients should not need to understand the internal database key or query strategy represented by the cursor.

The server is responsible for validating the cursor and determining the corresponding continuation position.

---

## Page Numbers and Cursors Are Distinct

The Java implementation explicitly rejects a request containing both:

`page`

and:

`cursor`

at the same time.

These mechanisms represent different pagination contracts.

A page-number request asks for a position in a logical page sequence.

A cursor request asks for a continuation from a previously issued position.

Combining both creates ambiguity because the server would need to decide which mechanism has priority.

The SQL schema also enforces this rule through:

`CHECK (NOT (page_number IS NOT NULL AND cursor_value IS NOT NULL))`

This is an example of a rule that belongs at the persistence boundary because invalid states should not be stored.

---

## Python Implementation

The Python program is a complete standard-library HTTP service.

Its resource model is an in-memory collection of `Book` objects. The `BookRepository` provides persistence-like operations while keeping the demonstration dependency-free.

The route:

`GET /api/v1/books`

returns a paginated collection.

The route:

`GET /api/v1/books/{id}`

returns an individual resource.

The route:

`POST /api/v1/books`

creates a resource and returns `201 Created` together with a `Location` header pointing to the newly created resource.

The server rejects malformed JSON, missing fields, invalid years, empty strings, oversized request bodies, invalid pagination parameters, unknown resources, and deprecated URI usage.

The `ApiError` type creates a consistent error representation with:

- HTTP status;
- machine-readable error code;
- human-readable message;
- optional details.

This separation is useful for clients because a client can make decisions based on `code` without parsing human-oriented prose.

---

## JavaScript Implementation

The JavaScript program uses Node.js built-in HTTP functionality instead of an external web framework.

Its event-driven design demonstrates an important JavaScript-specific implementation characteristic. Request bodies are read asynchronously through the request stream.

The API supports:

`GET /api/v1/books`

`GET /api/v1/books/{id}`

`POST /api/v1/books`

and:

`GET /api/v1/health`

The `Map` structure provides direct in-memory lookup for individual resources.

The pagination function operates on a sorted array and produces navigation links.

The implementation also demonstrates asynchronous request execution through `Promise`-based client calls used to exercise the server.

This makes the JavaScript artifact more than a syntactic translation of the Python service. It uses Node.js streaming and event-driven request processing as part of the API implementation.

---

## C++ Governance Case Study

The C++ program moves one architectural layer below the HTTP server.

It models an API policy engine that evaluates requests before they are allowed to proceed.

The `ApiCatalog` stores:

- API versions;
- resource definitions;
- collection URIs;
- item URI templates;
- pagination strategies.

The `QueryParser` validates query parameter structure and positive integer values.

The `RestPolicyEngine` evaluates:

- supported HTTP methods;
- API namespace;
- API version;
- version lifecycle state;
- resource existence;
- pagination parameters;
- maximum page size;
- incompatible pagination parameters.

The engine produces a `ValidationResult` containing an HTTP-style status code, acceptance state, reason, and warnings.

This architecture reflects a production design in which transport code should not contain all business and policy logic. A gateway, service, or controller can delegate contract validation to deterministic domain components.

---

## Java Enterprise Model

The Java implementation uses explicit domain types for API governance.

`ApiVersion` represents version lifecycle state.

`ResourceDefinition` represents a resource collection and its item URI pattern.

`PaginationPolicy` defines defaults, limits, and supported pagination mechanisms.

`ApiRequest` represents a normalized incoming request.

`PolicyDecision` represents the result of contract validation.

The `ApiRegistry` acts as a catalog of version and resource definitions.

The `RequestValidator` applies the rules in a predictable order.

This separation is valuable in enterprise systems because routing, configuration, validation, and policy evaluation can evolve independently.

The Java implementation also uses `Optional` for version and resource lookup, records for immutable domain representations, an enum for pagination type, and explicit exceptions for invalid policy configuration.

---

## SQL Data Model

The PostgreSQL model separates API governance into relational entities.

`api_versions` stores version lifecycle information.

`api_resources` stores resource definitions.

`api_resource_versions` connects resources to version-specific URI contracts.

`pagination_policies` stores pagination rules.

`api_clients` represents consumers of the API.

`api_requests` records actual request behavior and policy outcomes.

Foreign keys prevent references to nonexistent versions or resources.

Unique constraints prevent duplicate version identifiers and resource URIs.

Check constraints prevent invalid pagination states.

For example, this rule prevents a request from simultaneously recording a page number and cursor:

`CHECK (NOT (page_number IS NOT NULL AND cursor_value IS NOT NULL))`

The database therefore becomes a second enforcement boundary rather than relying entirely on application code.

---

## Resource and Version Relationship

A resource can have different representations under different API versions.

For example:

`/api/v1/books`

and:

`/api/v2/books`

can identify the same conceptual resource while representing different API contracts.

The `api_resource_versions` table captures this relationship.

This is preferable to assuming that a version is merely a string appended to every table name. API versioning is a contract concern, while the underlying persistence model can remain stable when the domain permits it.

---

## Error Semantics

The implementations use several HTTP status classes deliberately.

`200 OK` indicates successful retrieval or policy acceptance.

`201 Created` indicates successful creation of a new resource.

`400 Bad Request` is used for malformed or invalid request parameters.

`404 Not Found` represents an unknown resource or unsupported resource URI.

`405 Method Not Allowed` represents a method that the resource does not support.

`410 Gone` represents a deliberately retired contract.

`413 Payload Too Large` protects the service from excessive request bodies.

`422 Unprocessable Entity` is used in the Python implementation when a syntactically valid JSON field violates a domain validation rule.

`500 Internal Server Error` represents an unexpected server-side failure.

The exact error policy should be documented as part of the API contract and applied consistently.

---

## Filtering and Pagination

Filtering changes the collection before pagination.

For example:

`/api/v1/books?category=api-design&page=1&page_size=20`

should conceptually perform:

`filter → stable ordering → pagination`

rather than paginating the entire collection and then filtering each page.

If filtering happens after pagination, a page could contain very few matching records even though later pages contain more matches.

The Python and JavaScript implementations apply filtering before the pagination slice.

---

## Stable Ordering

Pagination requires deterministic ordering.

If a database query does not specify an order, the database is not required to return rows in a stable sequence.

A request such as:

`SELECT ... LIMIT 20 OFFSET 20`

without an explicit ordering can therefore produce unstable pagination behavior.

A production implementation should use an explicit order, ideally including a unique tie-breaker.

For example:

`ORDER BY created_at DESC, id DESC`

provides deterministic ordering when multiple resources have the same creation timestamp.

The Python and JavaScript demonstrations use resource IDs as the stable ordering key.

---

## Offset Pagination and Database Cost

Offset pagination is conceptually simple but can become expensive at large offsets.

A request such as:

`OFFSET 900000 LIMIT 50`

may require the database to identify and discard a large number of preceding rows before producing the requested page.

Cursor or keyset pagination can avoid this behavior when the data access pattern supports it.

A keyset query can use an indexed ordering key such as:

`WHERE id < :last_seen_id`

combined with:

`ORDER BY id DESC`

and:

`LIMIT :page_size`

The appropriate strategy depends on the resource's ordering semantics and consistency requirements.

---

## API Contract Stability

A URI is part of the public contract.

Changing:

`/api/v1/books`

to:

`/api/v1/library-items`

without a compatibility strategy can break clients even if the underlying data is unchanged.

Similarly, changing the meaning of a query parameter can be an incompatible change.

For example, if `page_size=20` previously meant "return at most 20 resources" and later begins meaning "return approximately 20 resources depending on server load", the contract has changed.

Versioning should therefore consider semantics, not only JSON field names.

---

## Common URI Design Failures

A controller-oriented design often creates URIs such as:

`/api/v1/getBooks`

`/api/v1/createBook`

`/api/v1/deleteBook/42`

These addresses encode operations into resource names.

A resource-oriented design instead uses:

`GET /api/v1/books`

`POST /api/v1/books`

`DELETE /api/v1/books/42`

The HTTP method expresses the requested operation while the URI identifies the resource.

Another failure is exposing database implementation details directly:

`/api/v1/sql/tables/books`

The API should expose a domain resource, not the internal storage mechanism.

---

## Pagination Failure Modes

Pagination can fail in several technically different ways.

An unlimited page size can create resource exhaustion.

An unstable ordering can produce duplicates or missing resources between pages.

A changing dataset can make page-number positions shift.

An expensive count query can make `total_items` costly for very large datasets.

A cursor can become invalid if its underlying representation is not stable.

A client may also incorrectly assume that an empty page means that the collection is permanently empty.

The API contract should define how these conditions behave.

---

## Security Considerations

Pagination parameters should be validated before they reach database queries.

The API should not interpolate raw query parameters into SQL.

Prepared statements or parameterized database APIs should be used for database access.

Maximum page sizes reduce accidental or malicious resource consumption.

Opaque cursors should not expose sensitive database information.

Error responses should avoid revealing internal database schema, stack traces, credentials, filesystem paths, or infrastructure details.

Version migration information can be useful, but sensitive deployment information should not be placed in public API errors.

The Python and JavaScript examples enforce request-body size limits and structured validation. The SQL model adds database-level integrity constraints.

---

## Production Considerations

An actual production API would normally place an HTTP server, reverse proxy, API gateway, or framework around the domain logic demonstrated here.

The core rules should still remain explicit:

- URI construction should be deterministic.
- Version lifecycle should be observable.
- Pagination limits should be enforced.
- Collection ordering should be stable.
- Errors should have predictable structures.
- Resource identifiers should remain stable.
- Deprecated contracts should have a defined migration policy.
- Retired contracts should have explicit behavior.
- Query parameters should be validated.
- Database constraints should protect important invariants.

Caching also requires care. A collection URI with query parameters can represent different representations, so cache keys must incorporate the relevant query state.

For authenticated APIs, authorization should be evaluated before exposing protected resource representations. Pagination must not become a mechanism for discovering resources that the caller is not authorized to access.

---

## Relationship Between the Three Core Areas

URI design, versioning, and pagination solve different problems.

**URI design** answers:

"What resource does this request identify?"

**Versioning** answers:

"Which API contract governs the meaning of this request?"

**Pagination** answers:

"How should a potentially large collection be divided into manageable representations?"

A request such as:

`GET /api/v1/books?category=api-design&page=2&page_size=20`

contains all three concerns.

The URI identifies the `books` collection.

`v1` identifies the API contract.

`category`, `page`, and `page_size` control collection retrieval.

These concerns should remain conceptually separate even though they appear together in the same HTTP request.

---

## Implementation Comparison

| Implementation | Primary technical perspective |
| --- | --- |
| Python | Complete standard-library HTTP API with resource routing and pagination |
| JavaScript | Event-driven Node.js API with asynchronous request-body processing |
| C++ | API governance and request-policy engine |
| Java | Enterprise domain model and validation service |
| PostgreSQL | Durable API registry, pagination policy, and request-governance data model |

The implementations intentionally do not reproduce the same program in five languages. Each one emphasizes a different architectural responsibility while preserving the same API design principles.

---

## Practical Request Flow

A production request can be viewed as a sequence of contract decisions:

`HTTP request`

→ URI parsing

→ API version resolution

→ resource resolution

→ authorization

→ query validation

→ filtering

→ stable ordering

→ pagination

→ database access

→ representation creation

→ HTTP response

Versioning is evaluated before interpreting version-specific resource rules.

Pagination is evaluated before an expensive collection query.

Stable ordering is applied before page slicing.

Database constraints remain a final integrity boundary.

This separation prevents URI routing, version management, pagination, and persistence concerns from becoming one undifferentiated block of controller logic.

---

## Important Design Distinctions

A **resource URI** identifies a thing.

A **query parameter** modifies how a collection is retrieved.

An **API version** identifies the contract governing the resource representation.

A **page number** represents a position in a page-oriented collection model.

A **cursor** represents continuation from a previously established position.

A **pagination policy** defines acceptable collection retrieval behavior.

A **database constraint** protects persistent data integrity.

Keeping these distinctions explicit makes the API easier to evolve, test, observe, and operate.
