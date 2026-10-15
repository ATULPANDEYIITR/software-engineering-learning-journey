# Authentication: Sessions, Tokens, and Authentication Flows

## Scope

This learning artifact treats authentication as a system of related mechanisms rather than as a single login operation. The implementations distinguish identity verification, authenticated state, credential transport, credential lifetime, revocation, refresh, and authorization.

The four central mechanisms are:

| Mechanism | Primary purpose | State characteristics | Main security concern |
|---|---|---|---|
| Password authentication | Establish that the presented secret matches the registered identity | Server-side user record | Credential theft and offline password attacks |
| Sessions | Maintain authenticated state between requests | Stateful | Session theft, fixation, expiration, revocation |
| Access tokens | Carry authenticated identity and claims between requests | Commonly stateless | Token theft, signature validation, expiry |
| Refresh tokens | Obtain new short-lived access credentials | Stateful in the demonstrated design | Replay, rotation, revocation |

The Python implementation provides a complete authentication service with password verification, stateful sessions, access tokens, refresh-token rotation, authorization checks, rate limiting, and security failure handling.

The JavaScript implementation models an event-driven authentication service suitable for understanding how authentication fits into Node.js request processing.

The C++ implementation presents an enterprise repository-administration case study in which authentication state is explicitly modeled and audited.

The Java implementation uses domain-oriented classes and state transitions to represent an enterprise authentication service.

The PostgreSQL implementation moves authentication state and integrity rules into a relational model.

## Authentication as a flow

Authentication begins with an authentication factor and ends with an authenticated security context.

A password flow can be represented conceptually as:

`credentials -> verification -> authenticated identity -> session/token -> authorization -> protected operation`

These stages must not be treated as interchangeable.

Credential verification answers:

> Who is this user?

Session or token validation answers:

> Is the previously established authentication state still valid?

Authorization answers:

> Is this authenticated identity permitted to perform this operation?

The implementations intentionally preserve these boundaries.

A user can be authenticated but still fail authorization. For example, the Python, C++, and Java programs create users with ordinary roles and then attempt administrator authorization. Authentication succeeds because the identity is valid, while authorization fails because the required role is absent.

## Password authentication

The Python program uses PBKDF2 through the standard library rather than storing a password directly. The stored representation contains the hashing algorithm, work factor, salt, and derived value.

The important property is that authentication verifies a password against a stored verifier rather than recovering the original password.

The Python `hash_password()` function creates a random salt and derives a key with PBKDF2-HMAC-SHA-256. `verify_password()` reconstructs the derivation and compares the result with `hmac.compare_digest()`.

The JavaScript program uses Node.js `crypto.pbkdf2Sync()` to demonstrate the same security boundary while using a JavaScript-specific API.

The C++ and Java programs deliberately use dependency-free digest-like demonstrations so that they can compile with the requested standard toolchains. Their comments explicitly state that those simplified functions are not production password-hashing algorithms. A real deployment should use a memory-hard or appropriately configured password-hashing mechanism rather than a fast general-purpose digest.

Passwords should never be placed in sessions, JWT payloads, logs, URLs, or refresh-token records.

## Credential verification and account state

A successful password comparison does not automatically mean that authentication should be accepted.

The implementations also consider account state.

A disabled account must not authenticate even when its password is correct. The Python, C++, and Java implementations demonstrate this distinction by checking the user's active status after locating the identity.

Account disablement also has implications for already issued authentication state. A system that only rejects future password logins could leave previously issued sessions and tokens usable. The C++ and Java implementations explicitly revoke existing sessions and access tokens when a user is disabled.

This creates a stronger containment boundary:

`disable account -> invalidate existing authentication state -> reject future authentication`

## Stateful sessions

A session represents authenticated state stored on the server.

The Python `Session` object contains:

- a random session identifier
- the associated user identifier
- creation time
- expiration time
- last-seen time
- CSRF token
- revocation state
- optional client metadata

The server-side `SessionStore` controls whether a session is still usable.

This provides a major operational advantage: revocation is immediate from the server's perspective. Logging out can mark the session as revoked without waiting for a token embedded in the client to expire.

The Python implementation also supports revoking all sessions belonging to a user. This is useful for password-reset events, account compromise response, administrative disablement, or forced logout.

The JavaScript implementation models the same idea with a `Map` because Node.js applications commonly maintain request-oriented state through services and storage layers.

The C++ implementation uses `unordered_map` to associate session identifiers with explicit session objects.

The Java implementation makes session lifecycle a domain object with `ACTIVE`, `REVOKED`, and `EXPIRED` states.

## Session fixation and session regeneration

A session identifier should not be treated as permanently associated with a browser before authentication.

The authentication boundary is an important point for session identifier regeneration.

In the Python, JavaScript, C++, and Java implementations, a new server-side session identifier is generated only after successful credential verification.

The relevant sequence is:

`unauthenticated request -> credential verification -> new authenticated session`

rather than:

`attacker-controlled identifier -> victim authentication -> same identifier becomes authenticated`

The regeneration behavior is a security property of the authentication transition, not merely a session-management convenience.

## Session expiration

Sessions in the examples have finite lifetimes.

A session becomes unusable when:

- it has been explicitly revoked
- its expiration time has passed
- its owning account is no longer active

The Python `Session.is_valid()` method centralizes these checks.

The Java `Session.isUsable()` method also changes an expired session to an explicit `EXPIRED` state. This makes the lifecycle visible to the enterprise domain model.

Expiration is different from revocation.

Expiration is normally time-driven.

Revocation is an explicit administrative or security action.

Both result in an authentication failure, but their operational meanings are different.

## Session cookies and browser security

The JavaScript implementation creates a representative secure session cookie using:

`HttpOnly`

`Secure`

`SameSite=Lax`

`Path=/`

`HttpOnly` prevents ordinary browser JavaScript from reading the cookie.

`Secure` instructs the browser to send the cookie only over HTTPS connections.

`SameSite` controls cross-site cookie transmission and can reduce cross-site request risks.

These attributes do not replace server-side authorization or CSRF defenses.

The Python session model also generates a CSRF token. A server-rendered or cookie-authenticated application can require the token for state-changing requests so that possession of the session cookie alone is insufficient for a cross-site request.

## Access tokens

An access token is a credential presented to a protected service after authentication has already occurred.

The Python and JavaScript programs implement a compact HS256-style signed token to make the mechanics visible.

The token contains claims such as:

- issuer
- subject
- issue time
- expiration time
- token identifier
- roles

The signing process conceptually creates:

`encoded header + "." + encoded payload -> HMAC signature`

Verification recomputes the signature over the received header and payload and compares it with the supplied signature.

The signature protects integrity. It does not make the token secret.

A signed token payload should therefore not be used as a place to store confidential information.

## Token validation

An access token is not valid merely because it has a syntactically correct three-part structure.

The Python and JavaScript implementations validate:

- token structure
- signing algorithm
- signature
- issuer
- subject
- expiration

The user represented by the subject is then checked against the server-side user store.

A token with a valid signature but a disabled user must still be rejected in these examples.

This illustrates the difference between cryptographic validity and application validity.

A cryptographically valid token can still fail an application-level security policy.

## Short-lived access tokens

The example access tokens have a short lifetime of approximately ten minutes.

Short lifetimes limit the useful period of a stolen access token.

This creates a trade-off.

A shorter lifetime reduces the exposure window but requires more frequent token renewal.

A longer lifetime reduces renewal traffic but increases the period during which a stolen token can remain useful.

The appropriate lifetime depends on the sensitivity of the application, client type, operational architecture, and threat model.

## Refresh tokens

Refresh tokens solve a different problem from access tokens.

An access token is intended for relatively frequent presentation to protected services.

A refresh token is intended to obtain another access token after the access token expires.

The Python, JavaScript, and SQL designs treat refresh tokens as stateful credentials. Only their hashes are stored in the demonstrated stores or relational tables.

This creates a server-side control point for:

- expiration
- revocation
- rotation
- replay detection

A refresh token should not simply be treated as an access token with a longer expiration period.

Its security properties and operational role are different.

## Refresh-token rotation

The demonstrated refresh flow uses rotation.

Suppose the current refresh token is `R1`.

A successful refresh produces:

`R1 -> R2`

The old token becomes unusable.

If an attacker later attempts:

`R1 -> another refresh`

the system rejects it because `R1` has already been rotated.

The Python `RefreshTokenStore.rotate()` method implements this behavior.

The JavaScript `RefreshTokenManager.rotate()` method stores the old token as revoked and creates a replacement.

The Java program uses an explicit `ROTATED` state.

The PostgreSQL function `rotate_refresh_token()` locks the current row with `FOR UPDATE` before checking and changing its state. This is important because concurrent requests must not both successfully rotate the same credential.

## Replay and concurrency

Refresh-token rotation introduces a state transition that must be atomic.

Without proper synchronization, two simultaneous requests could observe the same token as active:

`request A reads active`

`request B reads active`

`request A creates replacement`

`request B creates replacement`

The database implementation addresses this with a row-level lock inside the transaction.

This illustrates why authentication is not only a cryptographic problem. It is also a state-management and concurrency problem.

## Authentication versus authorization

Authentication establishes identity.

Authorization evaluates permissions.

The examples intentionally keep them separate.

A user with the role `reviewer` can successfully authenticate but should not automatically receive administrator privileges.

The Python `require_role()` function performs an explicit role check.

The JavaScript `authorize()` function performs the same policy decision through a JavaScript `Set`.

The Java model uses domain methods such as `hasRole()` and `authorize()` rather than embedding the policy only in output statements.

The SQL model represents roles and user-role assignments with separate relational tables.

This separation allows authentication mechanisms to remain stable while authorization policies evolve.

## Python implementation

The Python program is the most complete executable service model.

It contains:

- PBKDF2 password verification
- user registration
- password authentication
- stateful sessions
- CSRF token generation
- short-lived signed access tokens
- refresh-token rotation
- role-based authorization
- login throttling
- logout
- global session revocation
- account-state checks
- malformed-token handling
- replay detection
- secure-cookie policy demonstration

The `AuthenticationService` acts as the orchestration layer.

`SessionStore` owns session lifecycle.

`RefreshTokenStore` owns refresh credential lifecycle.

`JwtCodec` owns access-token encoding and validation.

`LoginRateLimiter` handles repeated authentication failures.

This decomposition keeps credential types from becoming one undifferentiated authentication object.

## JavaScript implementation

The JavaScript program takes an event-driven perspective.

`AuthenticationService` extends `EventEmitter`, allowing authentication outcomes to generate events such as:

`authentication.failed`

`authentication.succeeded`

`authentication.logout`

This reflects the event-oriented nature of Node.js systems.

The program also demonstrates a Promise-based authentication flow. The asynchronous boundary is useful when authentication is connected to database queries, network calls, session stores, or external identity providers.

`SessionManager` maintains stateful sessions.

`RefreshTokenManager` handles token rotation.

`TokenService` handles signed access tokens.

`LoginThrottle` limits repeated authentication attempts.

The cookie helper demonstrates how browser-facing authentication state can be represented with security attributes.

## C++ case study

The C++ program models authentication for an enterprise repository-administration environment.

The system maintains:

- users
- sessions
- access tokens
- refresh tokens
- authentication events

The domain uses explicit state enumerations rather than representing lifecycle conditions only through Boolean flags.

For sessions:

`ACTIVE`, `REVOKED`, and `EXPIRED`

For refresh tokens:

`ACTIVE`, `ROTATED`, `REVOKED`, and `EXPIRED`

This is useful because authentication state transitions have different meanings and should not be reduced to a single `valid` flag.

The case study also demonstrates account disablement. Disabling a user revokes existing sessions and access tokens, which models an administrative containment action.

The audit log records authentication outcomes and their reasons. This is important for security investigations because a system should distinguish an unknown account, incorrect password, disabled account, expired credential, and successful authentication.

## Java implementation

The Java implementation models authentication as an enterprise domain.

The `User`, `Session`, `AccessToken`, and `RefreshToken` classes each own state relevant to their lifecycle.

The `AuthenticationService` coordinates these domain objects.

The `PasswordHasher` interface separates password verification policy from authentication workflow. This makes the domain service independent of one specific hashing implementation.

The Java implementation uses immutable collections when exposing roles and audit events. This prevents callers from silently modifying security state through returned collections.

The explicit `AuthenticationResult` record groups the credentials returned after successful login.

The service also implements account disablement as a state transition that invalidates existing authentication artifacts.

## SQL data model

The PostgreSQL schema separates authentication concepts into relational entities.

`users` represents identities and account status.

`roles` represents available authorization roles.

`user_roles` represents role assignments.

`sessions` stores stateful authenticated sessions.

`access_tokens` stores hashed token references and expiration state.

`refresh_tokens` stores hashed refresh credentials and their rotation relationships.

`authentication_events` provides an audit trail.

This separation avoids putting unrelated security state into one large table.

## Database constraints

The SQL model uses database constraints to enforce rules that should not depend entirely on application code.

The `users` table ensures that usernames are nonblank and uses a case-insensitive unique index so that two accounts cannot be created with different capitalization of the same username.

Session and token tables require expiration times to occur after issuance.

Refresh-token rotation requires a replacement reference when the state becomes `rotated`.

The database therefore acts as an additional enforcement boundary.

Application validation remains necessary, but database integrity prevents a class of inconsistent states even when multiple application paths write the data.

## SQL transactions and refresh rotation

The `rotate_refresh_token()` PostgreSQL function uses `SELECT ... FOR UPDATE`.

The lock prevents concurrent refresh requests from simultaneously consuming the same active refresh token.

The operation then:

- retrieves the token
- confirms that it exists
- verifies that it is active
- verifies that it has not expired
- creates a replacement
- marks the old credential as rotated
- records the replacement relationship

This is a database-level state transition.

The operation is materially different from simply running an update against a token row because concurrency and replay semantics must be preserved.

## Authentication audit data

Authentication events are stored independently from credentials.

The audit table records:

- the user when known
- authentication method
- success or failure
- reason
- source IP
- timestamp

It does not store the password or raw access token.

Failure queries can therefore identify repeated authentication failures without exposing authentication secrets.

The partial index on failed authentication events supports investigations focused on unsuccessful attempts.

## Edge cases represented by the implementations

A missing username is treated differently from a disabled account.

An incorrect password produces an authentication failure.

A malformed access token is rejected before authorization.

An expired session cannot authenticate.

A revoked session cannot authenticate.

A disabled account cannot use previously issued authentication state in the C++ and Java models.

A refresh token cannot be reused after rotation.

A user can authenticate successfully and still fail an authorization check.

A cryptographically valid access token can still fail application-level validation when its subject is disabled.

These distinctions are important because collapsing all failures into a single generic validity flag makes security behavior harder to reason about.

## Common implementation mistakes

### Treating authentication and authorization as the same operation

A successful password check proves an identity claim. It does not establish that the identity can perform every protected operation.

### Storing raw passwords

Passwords should be transformed with a password-specific hashing scheme and never stored in plaintext.

### Making long-lived access tokens

A stolen access token with a long lifetime increases the attacker's usable window.

### Treating refresh tokens as permanent credentials

Refresh tokens should have explicit lifetime, revocation, and rotation behavior.

### Reusing session identifiers across authentication boundaries

A new authenticated session identifier reduces session-fixation risk.

### Logging credentials

Authentication logs should contain useful security context without recording passwords, session secrets, access tokens, or refresh tokens.

### Ignoring account state after token issuance

A token that was valid when issued may need to become unusable after an account is disabled or compromised.

### Failing to make refresh rotation atomic

Concurrent requests can otherwise consume one refresh credential more than once.

## Security boundaries

Authentication state should be protected according to its sensitivity.

Passwords require strong password hashing.

Session identifiers and refresh tokens should be generated from cryptographically secure randomness.

Access tokens require signature verification and strict claim validation.

Browser cookies require appropriate transport and script-access controls.

Authentication events should be auditable without leaking credentials.

Administrative actions such as disabling an account should invalidate relevant authentication state when immediate containment is required.

Authorization must be evaluated against trusted identity and policy data rather than against client-supplied role information.

## Performance considerations

Password hashing is intentionally expensive. That cost is useful because password verification is designed to resist high-speed guessing.

Access-token signature verification can be cheaper than repeated database lookups, which is one reason short-lived signed tokens are commonly used in distributed architectures.

Stateful sessions require a lookup for each request unless session state is cached.

Refresh-token rotation requires stateful storage because the server needs to know whether a credential has already been consumed.

Authentication event storage can grow quickly in high-volume systems. Indexes and retention policies therefore matter operationally.

Database locking around refresh-token rotation protects correctness but introduces contention if the same credential is incorrectly presented concurrently at high volume.

## Production considerations

The examples expose the mechanics without introducing external framework dependencies. A production implementation would need stronger infrastructure around those mechanisms.

Password hashing should use a dedicated, appropriately configured password-hashing implementation.

Session state should normally be stored in a durable or distributed session store when multiple application instances are involved.

Access-token signing keys require secure storage and controlled rotation.

Refresh tokens should be protected against replay and should have explicit revocation semantics.

TLS should protect credentials and authentication tokens during network transmission.

Authentication endpoints should implement rate limiting and monitoring.

Cookies should be configured according to the browser application architecture and CSRF model.

Token claims should be narrowly scoped and should not contain unnecessary sensitive information.

Administrative authentication changes should be auditable.

The security design should also define how password changes, account recovery, credential compromise, global logout, device revocation, and key rotation affect existing sessions and tokens.

## Relationship between the implementations

The six files intentionally use different perspectives.

The Python program emphasizes a complete executable authentication service and explicit credential lifecycle management.

The JavaScript program emphasizes event-driven behavior and browser-oriented authentication handling.

The C++ program emphasizes a coherent enterprise security case study with explicit lifecycle states and an audit model.

The Java program emphasizes domain modeling, service boundaries, immutable views, interfaces, and explicit authentication state transitions.

The SQL script emphasizes relational integrity, database constraints, indexes, transaction boundaries, and stateful credential persistence.

Together they model the same security domain without reducing each language to a translation of another implementation.
