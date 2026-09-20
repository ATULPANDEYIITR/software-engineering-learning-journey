<!-- File: README.md -->

# Defensive Error Handling Lab

## Topic

This repository demonstrates three closely related software engineering practices:

- exceptions
- input validation
- defensive programming

The implementation uses Python as the primary application layer, JavaScript for browser-side validation and exception handling, and C++ for a compiled implementation using standard-library exception mechanisms.

The examples model a small account service because it provides useful failure conditions without requiring an external database or payment system.

## Project purpose

Error handling is not limited to placing a `try` statement around every operation. A reliable application should decide which conditions are expected, validate untrusted input before using it, preserve valid application state when an operation fails, expose useful errors to callers, and avoid hiding unexpected failures.

This project separates three categories:

1. Validation errors occur when supplied data does not satisfy the required format or basic constraints.
2. Business-rule errors occur when structurally valid data violates an application rule.
3. Unexpected errors represent conditions that the application did not deliberately model and should normally be logged rather than silently ignored.

The account example uses a transaction limit of 100000.00, rejects non-positive amounts, prevents withdrawals above the current balance, and rejects duplicate account identifiers.

## Repository structure

`src/python_app/errors.py` contains the Python exception hierarchy.

`src/python_app/models.py` contains validated domain data and reusable input validation.

`src/python_app/service.py` contains account operations and business rules.

`src/python_app/cli.py` contains the executable Python demonstration and the outer exception boundary.

`tests/test_models.py` tests primitive validation and domain invariants.

`tests/test_service.py` tests service behavior, invalid input, business failures, and state preservation.

`web/index.html` provides the browser interface.

`web/app.js` implements JavaScript validation, custom errors, and controlled event handling.

`web/style.css` provides the browser presentation.

`cpp/main.cpp` contains a C++20 implementation of the same core ideas.

`CMakeLists.txt` defines the C++ build.

`Dockerfile` packages the Python demonstration.

`compose.yaml` provides a reproducible container invocation.

`.github/workflows/ci.yml` runs Python checks, builds the C++ program, and validates the browser JavaScript.

## Prerequisites

For the Python implementation:

- Python 3.11 or newer
- pip

For the browser implementation:

- a modern browser
- a local static HTTP server is recommended

For the C++ implementation:

- CMake 3.20 or newer
- a C++20 compiler

For container execution:

- Docker

## Installation

Create a virtual environment:

`python -m venv .venv`

Activate it on Windows PowerShell:

`.venv\Scripts\Activate.ps1`

Activate it on Linux or macOS:

`source .venv/bin/activate`

Install the project and development tools:

`python -m pip install -e ".[dev]"`

## Running the Python implementation

Run the demonstration directly:

`python -m src.python_app.cli`

The command creates an account, performs successful transactions, and deliberately triggers several expected failures.

The project also exposes the same application through the installed console command:

`error-handling-demo`

## Python exception model

The Python implementation defines `ApplicationError` as the parent for expected application-level failures.

`ValidationError` represents malformed or unacceptable external input.

`BusinessRuleError` represents input that is valid in structure but not permitted by the application's business rules.

`ResourceNotFoundError` represents an attempt to access an account that does not exist.

`StorageError` is defined as an extension point for storage-related failures. The current repository uses in-memory storage, so no storage exception is raised during normal execution.

The distinction matters because callers can catch an expected category without accidentally suppressing unrelated programming failures.

For example, the command-line application catches `ApplicationError` for expected failures. Its outer boundary separately catches `Exception`, logs the complete traceback, and re-raises the unexpected failure.

## Validation

Validation should happen at trust boundaries.

The account service treats method arguments as externally supplied values even though the current demonstration calls those methods internally.

The amount validator performs the following checks:

- the value can be converted to a decimal number
- the number is finite
- the number is greater than zero
- the value is normalized to two decimal places

The account identifier validator checks:

- the input is a string
- surrounding whitespace is removed
- the resulting value is not empty
- the identifier length is limited
- only letters, numbers, and hyphens are permitted

Validation is deliberately separated from business rules. A negative transaction amount is invalid input. A withdrawal greater than the current balance is structurally valid input that violates a business rule.

## Defensive programming

Defensive programming means designing software on the assumption that inputs, state, dependencies, and execution conditions can be different from what the caller expects.

This project applies several defensive techniques.

### Validate before mutation

The withdrawal method validates the amount and checks the balance before changing the account.

A failed withdrawal therefore does not partially change the account.

### Do not expose mutable internal state unnecessarily

The Python service returns a new list from `list_accounts()` rather than returning its internal dictionary or its internal dictionary values directly.

### Use specific exceptions

The implementation does not use one generic error type for every condition.

Specific exceptions allow callers to handle expected failures at the correct level.

### Preserve exception context

Python exceptions are raised with `from exc` when a lower-level exception is translated into an application-level exception.

This preserves the original exception as the cause and helps debugging.

### Avoid broad exception swallowing

This pattern is intentionally avoided:

`try: operation()`

`except Exception: pass`

Silently ignoring all failures can leave an application in an unknown state and makes diagnosis difficult.

## Exception handling principles

An exception should represent an exceptional control-flow condition rather than ordinary validation that can be cheaply handled through normal return values in every design.

The project uses exceptions where an operation cannot fulfill its contract.

A useful exception boundary generally performs three tasks:

1. identify an expected failure
2. convert it into a meaningful response or user message
3. allow unexpected failures to remain visible to logging and diagnostics

Catching an exception does not automatically mean the problem has been solved. The handler should either recover safely, communicate the failure, translate it into a suitable abstraction, or terminate the operation.

## Expected versus unexpected failures

Expected failures include:

- invalid account identifiers
- empty owner names
- invalid amounts
- duplicate accounts
- missing accounts
- insufficient funds
- transactions above the configured limit

Unexpected failures include conditions such as programming defects or system-level failures that the application has not explicitly modeled.

Expected failures are handled close to the interface where useful feedback can be produced.

Unexpected failures are logged with a traceback at the outer application boundary.

This distinction prevents the common mistake of converting every failure into a vague message such as "Something went wrong."

## JavaScript implementation

The browser implementation demonstrates the same principles using JavaScript `Error` subclasses.

`ValidationError` represents invalid input.

`BusinessRuleError` represents an operation that violates an application rule.

`parsePositiveAmount()` validates browser input before it reaches the state-changing functions.

`deposit()` updates the state only after validation succeeds.

`withdraw()` checks the available balance before mutation.

The event handlers call `executeOperation()`, which handles known application errors and reports unexpected errors separately.

Open `web/index.html` directly in a browser for a simple local demonstration.

For a local HTTP server, from the repository root run:

`python -m http.server 8080 --directory web`

Then open `http://localhost:8080`.

## C++ implementation

The C++ implementation uses custom classes derived from `std::runtime_error`.

`ApplicationError` establishes a common application exception type.

`ValidationError`, `BusinessRuleError`, and `ResourceNotFoundError` specialize that hierarchy.

The `AccountService` uses `std::unordered_map` for account storage.

The service validates transaction values before changing the account.

The withdrawal operation checks the balance before subtraction, which preserves the invariant that an account cannot become negative.

The `main()` function catches expected application exceptions before a final `std::exception` boundary handles other standard-library failures.

The project uses C++20 because `unordered_map::contains()` provides a direct and readable existence check.

## Building C++

Configure the build:

`cmake -S . -B build`

Build the executable:

`cmake --build build --config Release`

On Linux or macOS, run:

`./build/error_handling_demo`

On Windows with a Visual Studio generator, the executable is normally located under the generated configuration directory.

The exact executable location depends on the CMake generator.

## Testing

Install development dependencies:

`python -m pip install -e ".[dev]"`

Run all Python tests:

`pytest`

The test suite checks:

- valid amount conversion
- zero amounts
- negative amounts
- non-numeric amounts
- invalid account balances
- account creation
- duplicate accounts
- missing accounts
- deposits
- withdrawals
- insufficient balance
- transaction limits
- invalid identifiers
- preservation of state after a failed withdrawal

The state-preservation test is important because error handling should prevent failed operations from leaving partially modified state.

## Static analysis

Run Ruff linting:

`ruff check .`

Check Python formatting:

`ruff format --check .`

The GitHub Actions workflow runs both checks automatically.

## Docker

Build the container:

`docker build -t defensive-error-handling-lab .`

Run it:

`docker run --rm defensive-error-handling-lab`

The image runs the Python demonstration as a non-root user.

The image intentionally does not contain development tests or the browser and C++ portions because the container is designed specifically for the Python executable demonstration.

## Docker Compose

Run the Python application with Compose:

`docker compose up --build`

The Compose configuration uses the repository Dockerfile and passes non-secret environment variables explicitly.

No credentials are required by this project.

## Error categories

| Category | Example | Handling |
|---|---|---|
| Validation failure | `-10` transaction | Reject before business processing |
| Business-rule failure | Withdrawal above balance | Reject without changing state |
| Missing resource | Unknown account | Raise `ResourceNotFoundError` |
| Unexpected failure | Unmodeled runtime failure | Log and propagate |

## Defensive validation order

A practical validation sequence is:

1. Check that the value has an acceptable type or representation.
2. Normalize it where normalization is safe.
3. Check basic structural constraints.
4. Check domain-specific constraints.
5. Check business rules involving current state.
6. Mutate state only after all required checks succeed.
7. Return the successful result.

The exact order depends on the application, but state mutation should generally happen after the checks required to establish the operation's safety.

## Error translation

Lower-level exceptions should not always cross every architectural boundary unchanged.

For example, the Python amount parser catches conversion-specific exceptions and translates them into `ValidationError`.

This gives the service layer a stable application-level abstraction without exposing implementation details such as the exact exception produced by the decimal parser.

The original exception remains available as the cause for debugging.

## Logging

The Python application logs successful account mutations at the informational level.

Unexpected top-level failures are logged with `logging.exception()`, which records the traceback.

Sensitive information should not be written into logs. In a real financial application, account identifiers, personal information, authentication tokens, and transaction details would need an explicit logging policy.

## Common mistakes

### Catching everything

A handler such as `except Exception` around every function can hide defects.

Broad handling is more appropriate at a small number of application boundaries where the program can log, translate, or terminate safely.

### Using exceptions for normal loops

Exceptions are not a replacement for ordinary control flow. If a condition is expected on most iterations, normal branching is generally clearer.

### Validating only at the frontend

Browser validation improves user experience but does not establish trust.

Server-side or domain-level validation must still validate values when a backend exists.

This repository therefore validates independently in Python, JavaScript, and C++.

### Mutating before validation

Changing state and then checking whether the operation was valid can produce partial failures.

Validation and business checks occur before mutation in the account operations.

### Returning vague errors

Messages such as "invalid request" provide little diagnostic value.

The examples distinguish invalid input, business-rule failures, and missing resources.

### Logging sensitive data

Errors should contain enough information to diagnose a problem without exposing secrets or unnecessary personal data.

### Ignoring exception context

When translating a low-level exception into a domain exception, retaining the original cause can make debugging significantly easier.

## Edge cases

The project explicitly handles:

- empty identifiers
- whitespace around identifiers
- invalid identifier characters
- identifiers that are too long
- empty owner names
- non-numeric amounts
- zero amounts
- negative amounts
- non-finite numeric values
- transactions above the configured maximum
- withdrawals above the current balance
- duplicate account creation
- missing account access
- failed operations that must not modify state

## Numerical considerations

The Python implementation uses `Decimal` for monetary values because binary floating-point arithmetic is not generally appropriate for exact financial decimal representation.

The JavaScript and C++ educational implementations use numeric floating-point values to keep the examples focused on error handling.

A production financial system should establish a precise monetary representation policy. Common choices include integer minor units such as cents or a decimal type supported by the application's runtime and database.

## Performance considerations

Account lookup in the Python dictionary and C++ unordered map is designed for average constant-time lookup.

Validation adds computation before an operation, but it also prevents invalid data from reaching later processing stages.

The examples intentionally use in-memory storage. They do not claim database, network, or distributed-system performance characteristics.

For larger systems, performance analysis should consider:

- validation cost
- exception frequency
- logging volume
- serialization and parsing
- database round trips
- lock contention
- network failures
- retry behavior
- memory usage

Exceptions can be more expensive than ordinary branching in some runtimes, so applications should avoid using exceptions as the normal mechanism for high-frequency, expected conditions where another design is clearer.

## Reliability considerations

Reliable error handling requires preserving useful invariants.

For the account example, the primary balance invariant is that the balance cannot become negative.

The service also guarantees that a failed withdrawal does not modify the balance.

In systems with persistent databases, these state transitions should normally be protected by database transactions and appropriate concurrency controls.

## Security considerations

The browser is treated as an untrusted environment.

Client-side validation is not a security boundary.

The repository contains no passwords, API keys, private keys, or production credentials.

The Docker image runs the application as a non-root user.

Error messages are deliberately specific for the educational application, but production systems should ensure that internal implementation details, stack traces, credentials, filesystem paths, and sensitive records are not exposed to external users.

Input validation should also be combined with context-specific controls such as authorization, output encoding, parameterized database queries, and rate limiting when those controls are relevant to the application.

## Production considerations

A production implementation would need additional infrastructure depending on its environment.

Relevant concerns include:

- persistent storage
- database transactions
- authentication
- authorization
- request IDs
- structured logging
- metrics
- distributed tracing
- retry policies
- timeout policies
- circuit breakers for unreliable dependencies
- centralized error reporting
- API error contracts
- graceful shutdown
- dependency security scanning
- backup and recovery procedures

These concerns are intentionally not simulated with unnecessary external services because the central subject of this repository is exception handling, validation, and defensive programming.

## API-style error structure

The Python application exceptions provide `to_dict()` so an API adapter could produce a stable structure such as:

`{"error": "validation_error", "message": "Amount must be greater than zero."}`

An HTTP application could map validation errors to a client-error status and unexpected failures to a generic server-error response while retaining detailed diagnostics in internal logs.

The repository does not include a web API because adding an HTTP framework would introduce infrastructure that is not required to demonstrate the core topic.

## Testing philosophy

Error-handling tests should not focus only on successful examples.

For each important operation, tests should cover:

- valid input
- boundary values
- malformed input
- business-rule violations
- missing resources
- state after failure

The most important property of an error test is often not merely that an exception was raised. It is also that the system remains in a valid state afterward.

## Configuration

`.env.example` documents two optional runtime settings:

`APP_ENV` identifies the execution environment.

`LOG_LEVEL` identifies the desired logging level.

The current Python demonstration does not require environment variables to execute. They are documented because production applications commonly externalize runtime configuration instead of embedding deployment-specific values in source code.

## Continuous integration

The GitHub Actions workflow performs three independent checks.

The Python job installs development dependencies, checks formatting, runs linting, and executes tests.

The C++ job configures and builds the C++ implementation and executes the resulting program.

The web job verifies JavaScript syntax with Node.js and checks that the required browser files exist.

No deployment credentials are stored in the workflow.

## Scope and limitations

The project uses in-memory account storage, so data disappears when the Python process exits.

The browser implementation stores state only in memory.

The C++ program is a command-line demonstration rather than a network service.

The project does not implement authentication or authorization because those mechanisms are separate concerns from the central error-handling topic.

The examples are educational implementations of production principles. A real application must adapt validation rules, error contracts, persistence, logging, concurrency controls, and security controls to its specific domain.
