# API Documentation, OpenAPI, Swagger, and API Contracts

## Scope and engineering objective

API documentation is an interface specification that describes how a client interacts with a service. It must identify the operations a service exposes, the inputs those operations accept, the outputs they return, the errors clients can encounter, and the security mechanisms that govern access.

This project treats API documentation as an engineering artifact that can be checked against a running implementation. Its examples use project management, equipment registration, and incident management APIs to illustrate different parts of the same discipline.

The central relationship is:

- **API contract:** defines the externally visible behavior that clients may rely on.
- **OpenAPI:** provides a machine-readable specification for HTTP APIs.
- **Swagger:** refers to a family of tools that work with OpenAPI documents, including documentation interfaces and specification editors.
- **Contract validation:** checks that the specification, implementation, and consumer expectations remain consistent.
- **API governance:** establishes release conditions for schema changes, authentication, response behavior, and version compatibility.

A syntactically valid document is not necessarily an accurate contract. An accurate contract is not necessarily enforced by the implementation. Both require independent validation.

## OpenAPI and Swagger are related, not interchangeable

OpenAPI is a specification format. An OpenAPI document describes API metadata, server addresses, paths, HTTP methods, parameters, request bodies, responses, schemas, and security requirements.

Swagger tooling consumes or edits that specification. A rendered Swagger interface can help developers inspect an operation, understand its parameters, and construct a request. The interface does not independently prove that the server behaves as documented.

An OpenAPI operation commonly contains:

| Element | Contract responsibility |
|---|---|
| `operationId` | Provides a stable identifier for a particular operation. It should be unique within the API description. |
| `parameters` | Defines path, query, header, or cookie inputs, including requiredness and serialization rules. |
| `requestBody` | Defines the body media type, schema, and whether a body is required. |
| `responses` | Describes supported HTTP status codes, response headers, media types, and body schemas. |
| `components.schemas` | Provides reusable data models referenced by operations. |
| `components.securitySchemes` | Defines authentication mechanisms such as HTTP bearer authentication. |
| `security` | Applies security requirements globally or to individual operations. |
| `servers` | Identifies the base URLs used to access the API. |

OpenAPI 3.1 aligns its Schema Object with JSON Schema 2020-12. This makes schema composition and validation more expressive than simplistic hand-written type checks. A production validator must understand the actual OpenAPI version and its associated schema dialect.

## Contract-first design

Contract-first development defines the public interface before implementing its handlers. This makes client expectations explicit and gives implementation and testing teams a shared reference.

A contract-first workflow typically follows this path:

    OpenAPI specification
            |
            v
    Structural and schema validation
            |
            v
    Implementation and client integration
            |
            v
    Request/response contract tests
            |
            v
    Compatibility analysis
            |
            v
    Release approval

Each stage detects a different failure class. Structural validation detects malformed specifications. Request validation detects unacceptable payloads. Runtime tests detect behavior that contradicts the specification. Compatibility analysis detects changes that can disrupt existing consumers. Release governance combines those results into a decision.

## Python implementation: executable contract and HTTP behavior

The Python script builds an OpenAPI 3.1 document from an explicit operation registry. It then runs a small API implementation against the same declared models.

### Schema validation

`validate_schema()` implements a focused subset of JSON Schema validation. It checks types, required object properties, unknown properties, enumerations, string lengths, regular-expression patterns, numeric bounds, array sizes, and array item schemas.

The distinction between integers and booleans is important in Python. Because `bool` is a subclass of `int`, a plain `isinstance(value, int)` check would incorrectly accept `True` as an integer identifier. The validator explicitly excludes booleans from integer and number types.

Validation issues contain a path such as `$.owner` or `$.items[2].id`. Paths make failures actionable because they identify the exact location of a malformed value.

The implementation deliberately documents its limitations. It does not support every JSON Schema keyword, reference composition, recursive schemas, conditional schemas, or all OpenAPI validation rules. The function is suitable for examining core mechanisms, not for replacing a standards-compliant validator.

### Operation registry and OpenAPI generation

`OperationContract` stores the operation identifier, HTTP method, path template, parameters, request schema, response mappings, and security requirement.

`build_openapi_document()` transforms that registry into a JSON-compatible OpenAPI document. Reusing the registry reduces the risk of manually maintaining two unrelated operation inventories.

The generated document includes a bearer security scheme and reusable schemas for project creation, project representation, project lists, updates, and errors.

`validate_openapi_document()` checks selected structural invariants, including unique operation identifiers, absolute paths, required path parameters, documented response descriptions, schema references, and the presence of the authentication scheme. It is intentionally not a full OpenAPI validator.

### Runtime conformance

`ProjectService` demonstrates the relationship between a documented contract and server behavior.

- `POST /projects` validates the request body, rejects duplicate names with `409 Conflict`, and returns `201 Created` with a `Location` header.
- `GET /projects` validates pagination bounds and returns an explicit collection representation.
- `GET /projects/{projectId}` distinguishes malformed identifiers from nonexistent resources.
- `PATCH /projects/{projectId}` accepts a nonempty set of permitted changes rather than treating a partial update as a complete replacement.
- `DELETE /projects/{projectId}` returns `204 No Content` without a response body.

The service returns `401 Unauthorized` when the required demonstration credential is absent. This establishes the difference between declaring authentication in OpenAPI and enforcing it at runtime.

The credential is only a test fixture. A real service needs verified token validation, authorization rules, secure secret management, and appropriate audit controls.

### Compatibility analysis

`compare_schema_compatibility()` detects common breaking changes in response schemas, including removed properties, newly required properties, removed enumeration values, and narrowed numeric ranges.

These changes matter because clients may depend on previously available fields or valid values. The checker is conservative and incomplete. It does not establish full compatibility across arbitrary schema composition, unions, nullable values, references, or serialization differences.

### Testing and artifact export

The `unittest` suite verifies contract structure, resource creation and retrieval, authentication failures, duplicate conflicts, invalid updates, deletion semantics, query encoding, and a representative schema compatibility failure.

Running the script executes these tests. Passing tests provides evidence for the covered cases, not proof of conformance for every possible request.

An OpenAPI JSON artifact can be exported with `--export`. Exporting is optional to avoid unexpectedly overwriting a file during a normal demonstration.

## JavaScript implementation: asynchronous API behavior and events

The JavaScript file uses an equipment registry to demonstrate a different concern: request processing in an asynchronous service and the separation between HTTP behavior, domain events, and contract checks.

### Route templates

`matchRoute()` matches concrete paths against templates such as `/equipment/{equipmentId}`. Literal segments must match, while named segments become path parameters.

The implementation separates route matching from handler execution. This makes it possible to detect ambiguous route configuration and to distinguish an unmatched route from a matched route containing an invalid identifier.

Path decoding is guarded against malformed percent encoding. In a production HTTP server, routing, canonicalization, proxy handling, and path decoding must be consistent across all layers to avoid request-smuggling and authorization inconsistencies.

### Request and response validation

`validateValue()` checks a focused schema subset, including type, required properties, unknown properties, string limits, numeric bounds, enumerations, and array items.

The service checks the request body before modifying its in-memory registry. Duplicate serial numbers produce `409 Conflict`, while invalid payloads produce `400 Bad Request`.

The response uses explicit status codes and headers. Successful registration returns `201 Created`, a JSON representation, and a `Location` header identifying the new resource.

The private JavaScript fields in `EquipmentService` prevent callers from directly accessing the registry. Snapshots are returned rather than exposing mutable stored objects.

### Event-driven behavior

The service emits an `equipment.registered` event after a successful registration. This illustrates a useful separation: the HTTP operation owns request validation and the HTTP response, while a listener can perform a separate audit action.

The `on()` method returns an unsubscribe function so that long-lived listeners can be removed. In a production service, listeners that perform critical external operations need explicit failure handling, durable delivery, and retry semantics. An in-memory event listener does not provide transactional delivery.

### HTTP lifecycle and domain restrictions

The example prevents retired equipment from returning to an operational state. This is a domain transition rule rather than a JSON schema rule.

JSON Schema can establish that `condition` must be one of the allowed values. It cannot, by itself, determine whether a transition from the stored state is permitted. That decision depends on current server-side state.

The code tests invalid authentication, duplicate registration, malformed request data, and invalid state transitions. These checks show why static schema validation and runtime behavior testing are complementary.

### Consumer expectations and schema evolution

The JavaScript compatibility function detects newly required properties and removed response fields. Consumer expectations can be more restrictive than the general API schema: a consumer may rely on a particular status code or response field even when another client does not.

A complete compatibility assessment should compare the old and new schemas semantically and exercise actual consumer expectations. Comparing serialized documents as raw text is insufficient because harmless changes in property order or formatting should not be treated as interface changes.

## C++ case study: release governance for an incident API

The C++ program models a release controller that decides whether an API candidate satisfies repository-level release conditions. Its focus is the relationship between a published contract and evidence from the implementation.

### Domain model

`ApiRelease` combines the candidate version, previous version, declared operations, implementation evidence, schema-validation result, contract-test result, and security-review result.

`OperationContract` records the HTTP method, path, documented status codes, accepted request fields, required fields, and authentication requirement. `ImplementationEvidence` records observed statuses, accepted fields, and whether authentication is enforced.

These types separate the specification from observations. A documented response is an assertion about intended behavior; an observed response is evidence of actual behavior. Neither should silently replace the other.

### Governance algorithm

`ContractGovernanceEngine::evaluate()` examines global release conditions and individual operations.

It detects:

- Duplicate or missing operation identifiers.
- Invalid absolute path definitions.
- Required request fields that are absent from the allowed-field set.
- Missing response definitions.
- Runtime status codes absent from the contract.
- Documented status codes without observed implementation evidence.
- Request fields accepted by the implementation but absent from the contract.
- Operations requiring authentication without corresponding enforcement evidence.
- Breaking changes that violate major-version policy.

Findings are represented as structured values containing severity, code, and explanation. A warning does not automatically block a release, while an error does.

The algorithm performs linear scans over operations, evidence, and sets. With hash-based lookup, the main work is approximately proportional to the number of operations and the number of fields and status codes inspected. The demonstration uses standard containers and avoids external dependencies.

### Release decision

The first candidate has passing schema validation, contract tests, and security review. The controller evaluates it against the declared operations and evidence.

The demonstration then introduces a missing rate-limit response definition and marks contract tests as failing. These are independent reasons to reject the candidate.

A later scenario introduces an implementation field that is not part of the documented request schema. This exposes a different defect: undocumented input behavior can become an accidental public interface, encouraging consumers to depend on a field the service has not promised to support.

A production release controller would obtain signed or otherwise trusted evidence from the build pipeline. A Boolean supplied by a caller is useful in a case study, but it is not proof that the corresponding check actually ran.

## Java implementation: typed enterprise governance

The Java program models the API release process through immutable domain records, explicit schema types, a governance service, and a controlled release-state machine.

### Typed domain records

`ApiVersion` validates nonnegative semantic-version components and implements comparison. `ApiOperation` requires a stable operation identifier, an absolute path, and at least one documented response. `ImplementationEvidence` records observed runtime behavior independently of the contract.

Records and defensive copies reduce accidental mutation of policy inputs. This matters when governance decisions need to be reproducible from a particular specification and test report.

### Request schema model

`SchemaField` captures a field's type, requiredness, optional enumeration, and string-length limits. `ObjectSchema.validate()` reports missing required properties, type mismatches, out-of-range string lengths, invalid enumeration values, and undocumented properties.

The model intentionally covers a limited subset of JSON Schema. It does not claim to support every OpenAPI schema feature, and a real service should use a standards-compliant validator for arbitrary contracts.

### Governance service

`ReleaseGovernanceService` combines schema-validation results, contract-test results, security-review results, versioning policy, response-status evidence, and request-field evidence.

The service distinguishes missing test evidence from a known failure. It also distinguishes an undocumented response from a documented response that has not been observed in the current evidence set.

The implementation's major-version rule is a policy decision, not a universal semantic-versioning algorithm. Some changes can be backward-compatible without requiring a major increment, while certain security and operational changes may require review independently of version numbering.

### Explicit state transitions

`ReleaseWorkflow` permits validation to begin only from `DRAFT`. Approval can occur only from `VALIDATING`. A rejected release can be reopened for correction, while an attempt to approve a release in an invalid state raises `IllegalStateException`.

This separates release lifecycle rules from the logic that computes findings. A release-state machine prevents a successful governance result from being applied through an invalid transition.

## PostgreSQL data model: relational governance and evidence

The SQL script creates an isolated `api_contract_lab` schema. Its tables represent API versions, specification artifacts, operations, schemas, parameters, request bodies, responses, consumers, test evidence, compatibility findings, and release decisions.

### Versioned specification artifacts

`api_services` identifies an API product. `api_versions` records semantic-version components and links a candidate to its predecessor. The uniqueness constraint on service and version components prevents duplicate version identities.

`contract_artifacts` stores the OpenAPI document as `JSONB`, its format, a SHA-256 digest, and validation evidence. The digest is a format-checked value; the database does not calculate or authenticate the digest. A trusted build process must compute it from the actual artifact and protect its provenance.

The schema-level check ensures the artifact is a JSON object with an OpenAPI version beginning with `3.`. This is only a basic database check. Full document validation belongs in an OpenAPI-aware validation pipeline.

### Operations, schemas, parameters, and responses

`api_operations` stores the HTTP method, path template, operation identifier, summary, and authentication requirement.

`schema_definitions` stores reusable JSON Schema objects. `operation_parameters` records the parameter name, location, requiredness, and schema. A check constraint requires path parameters to be required, reflecting OpenAPI path-parameter semantics.

`operation_request_schemas` links request media types to schemas. `operation_responses` links documented status codes to descriptions and optional response schemas. The model permits a `204 No Content` response without a schema or media type.

These relationships allow queries to inspect an operation without parsing every part of the original OpenAPI document.

### Consumer-driven expectations

`consumer_applications` identifies known client applications and their responsible teams. `consumer_contract_expectations` records the status codes and response properties expected by individual consumers.

A schema can permit behavior that a particular consumer does not handle. Recording consumer expectations makes compatibility analysis more precise than treating the API document as the only relevant source of risk.

The table captures expectations as data, but it does not replace consumer-driven contract tests. Those tests must still execute requests and verify responses against the consumer's actual assumptions.

### Test evidence and runtime observations

`contract_test_runs` stores suite-level results, total test counts, failure counts, execution time, and a JSON report. A constraint enforces consistency between the pass flag and the failure count.

`implementation_observations` records observed status codes, accepted request fields, and authentication enforcement. These observations can expose an undocumented status code or a mismatch between declared authentication and actual behavior.

Observations are evidence, not a substitute for comprehensive tests. Sampling can miss rare error paths, authorization failures, and boundary conditions.

### Compatibility findings

`compatibility_findings` connects an older API version to a candidate version. Each finding identifies an operation, severity, change code, description, and resolution time.

An unresolved error finding blocks approval in the release function. Warnings remain visible without automatically blocking release. The partial index on unresolved findings helps queries that repeatedly inspect open compatibility risks.

### Transactional release approval

`approve_api_release()` locks the release-candidate row with `FOR UPDATE`. This prevents concurrent approval attempts from independently validating and changing the same candidate state without coordination.

The function rejects approval when:

- The candidate is not in the validating state.
- The approver identity is blank.
- Schema validation or security review has not passed.
- A latest contract-test suite has failed.
- A passing runtime contract-test suite is absent.
- An observed HTTP status is undocumented.
- Authentication evidence contradicts the contract.
- An unresolved compatibility error exists.
- A declared breaking change does not increase the major version.

The function updates the candidate to `approved` only after the checks succeed. Its transaction and row lock provide database-level coordination, but they cannot independently establish that external validation or security-review claims are truthful.

The sample script intentionally seeds a candidate in `validating` state without approving it automatically. A trusted release pipeline should invoke approval after collecting the required evidence.

## API compatibility and version evolution

Compatibility must be assessed from the consumer's perspective, not solely from whether a new document is valid.

| Change | Typical risk | Reason |
|---|---|---|
| Remove a response property | Breaking | Existing clients may read the property. |
| Make an optional request property required | Breaking | Previously valid requests can fail validation. |
| Add an optional response property | Often compatible | Many clients ignore unknown fields, but strict deserializers may reject them. |
| Add an allowed enumeration value | Context-dependent | Clients with exhaustive switches may fail when they receive it. |
| Remove an enumeration value | Breaking | Previously valid inputs or outputs become invalid. |
| Change a documented status code | Potentially breaking | Clients may branch on the previous status. |
| Tighten numeric bounds | Potentially breaking | Requests accepted by the old contract may fail. |
| Change authentication requirements | High risk | Previously permitted requests may become unauthorized. |
| Change pagination defaults | Behaviorally significant | Clients may receive different result counts or ordering. |

Semantic versioning is a communication policy rather than an automated proof of compatibility. A schema diff can identify likely breaking changes, but its findings need to be interpreted against actual serialization rules, runtime behavior, and consumer expectations.

## Contract testing and release gates

A reliable API pipeline separates several checks because each answers a different question.

- **Specification validation** asks whether the OpenAPI document conforms to the applicable specification and schema rules.
- **Request validation** asks whether a specific request satisfies the declared input contract.
- **Response validation** asks whether the actual status, headers, media type, and body satisfy the documented response.
- **Consumer contract testing** asks whether the API preserves the assumptions made by its consumers.
- **Compatibility analysis** asks whether a proposed contract change may invalidate previously supported behavior.
- **Security testing** checks authentication, authorization, input handling, and error behavior independently of documentation correctness.
- **Release governance** decides whether the collected evidence satisfies the organization's release policy.

A release gate should reject undocumented runtime behavior instead of allowing an implementation to silently expand the public interface. It should also avoid assuming that the presence of a schema in a document means the runtime enforces that schema.

## Failure modes and production considerations

### Incorrect status codes

An operation may document only success responses while the server emits validation, authorization, conflict, or rate-limit responses. Clients then lack a reliable basis for error handling. Every intentionally supported response should have a documented meaning and, when applicable, a body schema.

### Misleading security declarations

A bearer security scheme describes how a client supplies credentials. It does not prove that a token is verified, that scopes are checked, or that the caller may access a particular resource. Authentication and authorization must be enforced by the service and tested separately.

### Incomplete schema validation

A custom validator may omit schema composition, reference resolution, nullable behavior, formats, discriminators, or media-type-specific behavior. Production systems should use a standards-compliant OpenAPI and JSON Schema implementation rather than extending a small educational validator indefinitely.

### Overly strict and overly permissive models

Rejecting all unknown properties provides strict input control but may complicate forward-compatible clients. Permitting arbitrary properties may expose accidental fields and conceal typos. The appropriate policy depends on the operation and should be explicit in the contract.

### Sensitive information in examples and errors

Documentation examples must use synthetic credentials and non-sensitive records. Error responses should avoid exposing secrets, stack traces, internal hostnames, or private infrastructure details. Specification artifacts should not contain production tokens or confidential data.

### Uncontrolled artifact drift

A specification can become stale when it is edited separately from implementation behavior. A build pipeline should validate the exact artifact being released, preserve its digest and provenance, run contract tests against the candidate service, and retain the validation reports used to make the release decision.

### False confidence from passing tests

Passing a finite suite means the tested conditions passed. It does not prove every path, status code, schema branch, concurrency condition, or authorization decision is correct. Test design should cover boundary values, malformed requests, duplicate resources, absent credentials, unauthorized access, error responses, and compatibility-sensitive fields.

## Running the implementations

Python requires only the standard library. Save the first implementation as `api_contract_lab.py` and run `python api_contract_lab.py`. To write `openapi.json`, pass `--export`.

JavaScript requires Node.js 18 or later. Save the second implementation as `api-contracts.js` and run `node api-contracts.js`. To export its generated artifact, pass `--export`.

C++ requires a C++17 compiler. Save the third implementation as `api_governance.cpp`, compile it with `g++ -std=c++17 -Wall -Wextra -Wpedantic api_governance.cpp -o api_governance`, and run the resulting executable.

Java requires JDK 17 or later. Save the fourth implementation as `ApiContractGovernance.java`, compile it with `javac ApiContractGovernance.java`, and run `java ApiContractGovernance`.

PostgreSQL users can execute the SQL script in a disposable database with permission to create schemas and functions. The script drops and recreates `api_contract_lab`; do not run it against a shared schema containing data that must be retained.
