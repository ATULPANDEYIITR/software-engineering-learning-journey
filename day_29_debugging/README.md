# Debugging Workflow, Breakpoints, Logs, and Root Cause Analysis

## 1. Topic Introduction

Debugging is the systematic process of finding, understanding, and correcting defects in software.

A useful debugging process does not begin with random code changes. It begins with evidence:

1. Observe the failure.
2. Reproduce it.
3. Define expected and actual behavior.
4. Minimize the failing case.
5. Inspect execution state.
6. Form hypotheses.
7. Collect evidence.
8. Isolate the faulty component.
9. Identify the root cause.
10. Apply a focused correction.
11. Add a regression test.
12. Verify related behavior.
13. Check performance, security, and operational effects.

The three implementations in this topic demonstrate the same discipline from different technical perspectives:

- Python emphasizes readable experimentation, exceptions, assertions, logging, and interactive debugging.
- JavaScript demonstrates runtime debugging, browser or Node.js inspection, asynchronous execution, state inspection, and diagnostic APIs.
- C++ presents a more structured technical case study involving a realistic order-processing system, domain classes, validation, exceptions, logging, regression tests, and performance measurement.

---

## 2. Fundamental Terminology

### Bug

A bug is a defect in software that causes behavior to differ from the intended behavior.

A bug may produce:

- an incorrect result
- an exception
- a crash
- incorrect state
- data corruption
- excessive resource usage
- a security weakness
- an intermittent failure
- incorrect interaction with another component

### Failure

A failure is the observable manifestation of incorrect behavior.

For example, if an order should cost 1,000 but the system produces 800, the incorrect price is the failure.

The failure is not necessarily the root cause.

### Symptom

A symptom is an observable effect that indicates something may be wrong.

A slow API response is a symptom. It does not establish whether the cause is:

- inefficient code
- a slow database query
- network latency
- contention
- excessive logging
- resource exhaustion
- an external service

### Root Cause

The root cause is the underlying condition responsible for the failure.

Root cause analysis therefore asks:

> What condition actually produced this failure, and what evidence proves it?

### Exception

An exception represents an abnormal condition detected during execution.

Examples include:

- invalid input
- missing configuration
- division by zero
- out-of-range indexing
- failed file access
- failed network operations
- invalid object state

### Stack Trace

A stack trace describes the chain of function calls that led to an exception or failure.

A stack trace is useful because it can show:

- the exception type
- the exception message
- the function where the error occurred
- the caller
- the caller's caller
- the execution path leading to the failure

### Breakpoint

A breakpoint pauses program execution at a selected location.

When execution pauses, a debugger can inspect:

- variables
- object state
- function arguments
- call stack
- control flow
- expressions
- threads or asynchronous state, depending on the debugger

### Log

A log is a recorded diagnostic event.

Typical log levels include:

- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL or equivalent high-severity levels

The exact levels depend on the platform and logging framework.

### Regression

A regression occurs when behavior that previously worked becomes broken after a change.

Regression tests convert discovered bugs into repeatable checks.

---

## 3. The Core Debugging Workflow

### Step 1: Observe

Record:

- what happened
- what should have happened
- when it happened
- where it happened
- which input caused it
- which environment was involved

Avoid modifying code before the failure is understood.

### Step 2: Reproduce

A reproducible failure is much easier to debug than an unexplained report.

A good reproduction identifies:

- exact input
- required state
- configuration
- software version
- execution path
- relevant external conditions

### Step 3: Minimize

Remove unnecessary variables from the failing case.

For example, instead of debugging an entire order containing 500 items, determine whether one item is sufficient to reproduce the failure.

A smaller reproduction reduces the number of possible causes.

### Step 4: Establish Expected Behavior

State the expected result precisely.

For example:

`subtotal = 1000`

`discount = 10%`

`expected total = 900`

Precise expectations make evidence easier to evaluate.

### Step 5: Inspect Evidence

Useful evidence includes:

- stack traces
- logs
- variable values
- state snapshots
- database results
- request and response metadata
- timing measurements
- test results
- source-code differences
- configuration differences

### Step 6: Form a Hypothesis

A hypothesis should be testable.

Weak approach:

> Something is wrong with pricing.

Stronger approach:

> The discount operation may be executed twice for the same order.

The second statement can be tested directly.

### Step 7: Isolate

Divide the execution path into logical boundaries.

For example:

`raw input -> parsing -> validation -> transformation -> calculation -> formatting`

Inspect the output at each boundary.

### Step 8: Identify the Root Cause

Do not stop at the first incorrect value.

Ask why the incorrect value occurred.

For example:

`Wrong total`

→ discount too large

→ discount applied twice

→ two components both perform discounting

→ discount responsibility is not centralized

The final discovery is more useful than simply changing the displayed total.

### Step 9: Apply a Focused Fix

The correction should address the identified cause.

Avoid unrelated refactoring during a focused production incident unless it is required for safety or correctness.

### Step 10: Add a Regression Test

The discovered failure should become an automated test whenever practical.

This prevents the same defect from silently returning.

---

## 4. Python Implementation

The Python implementation is a standalone educational program using the standard library.

It demonstrates:

- terminology
- debugging workflow
- exceptions
- validation
- assertions
- breakpoints
- conditional breakpoint concepts
- logging
- contextual logging
- root cause analysis
- hypothesis-driven debugging
- fault isolation
- diagnostic decorators
- regression tests
- edge cases
- performance measurements
- security-aware logging
- exception chaining
- state inspection
- an order-processing case study

### 4.1 Exceptions

The Python implementation uses explicit exceptions for invalid conditions.

For example, an average cannot meaningfully be calculated from an empty sequence. The program raises `ValueError` rather than silently returning an arbitrary value.

This distinction is important:

- invalid input should be detected
- the error should be communicated
- callers should decide how the error is handled

### 4.2 Assertions

Assertions are used for internal assumptions.

The Python program validates external-style inputs with explicit exceptions and uses `assert` for an internal invariant such as a calculated total not becoming negative after valid input has passed validation.

Assertions should not be treated as a replacement for validation of untrusted input.

### 4.3 Breakpoints

Python provides the built-in `breakpoint()` function.

A developer can place it at a point where state needs to be inspected.

Useful `pdb` commands include:

- `p variable` to inspect a value
- `n` to execute the next line
- `s` to step into a function
- `r` to run until the current function returns
- `c` to continue execution
- `l` to inspect source context
- `q` to quit

A breakpoint is most useful when the problem is easier to understand by inspecting state than by reading source code alone.

### 4.4 Conditional Breakpoints

The Python implementation demonstrates a conditional diagnostic branch for negative measurements.

In an IDE, the equivalent breakpoint can be configured to pause only when the condition becomes true.

Conditional breakpoints are particularly useful when:

- a loop executes thousands of times
- only one record is invalid
- the failure occurs only for a specific identifier
- a state variable reaches an unusual value

### 4.5 Logging

The Python `logging` module provides structured levels and configurable handlers.

The implementation demonstrates:

- DEBUG
- INFO
- WARNING
- ERROR
- exception logging

`logger.exception()` is particularly useful inside an exception handler because it records the error together with exception information.

### 4.6 Logging Context

The order-processing examples include identifiers such as:

- order ID
- user ID
- transaction ID

Context makes logs more useful because individual events can be associated with the same operation.

### 4.7 Exception Chaining

Python supports exception chaining with `raise ... from ...`.

The configuration example demonstrates an application-level `ConfigurationError` retaining its underlying parsing exception.

This allows an application to expose a meaningful domain-level error while preserving the lower-level cause for debugging.

---

## 5. JavaScript Implementation

The JavaScript implementation uses standard JavaScript and Node.js-compatible APIs.

It demonstrates:

- debugging terminology
- systematic workflow
- validation
- `console` diagnostics
- `debugger`
- conditional debugging
- stack traces
- asynchronous execution
- state inspection
- fault isolation
- root cause analysis
- regression tests
- performance measurement
- security-aware diagnostics
- error wrapping
- a realistic order-processing case study

### 5.1 The `debugger` Statement

JavaScript provides the `debugger` statement.

When developer tools or a compatible debugger are active, execution can pause at that statement.

The paused environment can expose:

- local variables
- function arguments
- object properties
- call stack
- scope
- execution flow

The statement is useful for temporary development diagnostics.

### 5.2 Console Diagnostics

JavaScript environments provide console methods such as:

- `console.debug()`
- `console.info()`
- `console.warn()`
- `console.error()`

The exact presentation and filtering behavior varies between browsers and Node.js environments.

Logging should communicate useful diagnostic information rather than produce large amounts of unstructured output.

### 5.3 Assertions

The implementation uses `console.assert()` to express internal assumptions.

Assertions are useful for detecting violated expectations during development.

They should not replace explicit validation of external input.

### 5.4 Stack Traces

JavaScript `Error` objects provide a stack representation in common JavaScript runtimes.

The stack can show the path through functions that led to an exception.

The implementation deliberately creates a division failure so that the stack can be inspected.

### 5.5 Asynchronous Debugging

Asynchronous execution changes the debugging problem because execution does not necessarily follow a simple linear sequence.

The implementation includes an asynchronous workflow using a Promise and `async`/`await`.

Important asynchronous debugging concerns include:

- ordering
- timing
- rejected Promises
- missing `await`
- race conditions
- stale state
- external-service failures
- timeout behavior

A failure that occurs only intermittently may require additional timestamps, correlation identifiers, or controlled reproduction.

### 5.6 State Inspection

The `ShoppingCart` class demonstrates a useful technique: compare state before and after a mutation.

For example:

`before -> removeItem() -> after`

If the resulting state violates an expected invariant, the state transition becomes evidence.

This approach is especially useful for:

- mutable arrays
- caches
- queues
- session state
- application stores
- objects shared between components

---

## 6. C++ Technical Case Study

The C++ program models an order-processing system.

The scenario includes:

- orders
- order items
- prices
- quantities
- discounts
- taxes
- currency rounding
- validation
- diagnostic logging
- exceptions
- regression tests
- performance measurement
- state inspection

### 6.1 Problem Being Modeled

The system must calculate an order total while ensuring:

1. product prices are valid
2. quantities are positive
3. discounts remain within valid bounds
4. tax rates remain within valid bounds
5. intermediate calculations can be inspected
6. failures can be diagnosed
7. discovered defects can become regression tests

### 6.2 Main Components

The case study contains several major components.

#### `Logger`

Provides basic diagnostic levels:

- DEBUG
- INFO
- WARNING
- ERROR

The class centralizes diagnostic output rather than scattering formatting logic throughout the application.

#### `OrderItem`

Represents:

- product identifier
- unit price
- quantity

Its `total()` method validates the item before calculating its contribution to the order.

#### `Order`

Represents:

- order identifier
- collection of items
- discount percentage

The class separates subtotal calculation from final total calculation.

#### `TestRunner`

Provides simple regression-test operations:

- expected true
- expected numeric value
- expected exception

The purpose is educational rather than to replace a full production testing framework.

---

## 7. Price Calculation Pipeline

The C++ implementation separates the pricing pipeline into stages:

`raw amount -> parse -> tax -> round`

This design makes fault isolation easier.

Suppose the final result is wrong.

Instead of examining the entire calculation at once, inspect:

1. parsed amount
2. tax-adjusted amount
3. rounded amount

If the parsed amount is correct and the tax-adjusted amount is wrong, the fault boundary has already been narrowed.

This technique generalizes to larger systems:

`request -> validation -> transformation -> database -> business logic -> response`

Each boundary can be inspected independently.

---

## 8. Root Cause Analysis

Root cause analysis should be evidence-driven.

The case study uses the following incident:

> The customer receives a price lower than expected.

Possible hypotheses include:

- incorrect catalog price
- incorrect tax calculation
- duplicate discount application
- currency rounding problem

Evidence identifies that:

- catalog prices are correct
- tax calculation is correct
- the discount is applied twice
- removing the duplicate operation restores the expected result

The root cause is therefore the duplicate discount operation.

The corrective action is to centralize discount responsibility and add a regression test.

This illustrates an important debugging distinction:

**Symptom:** wrong total.

**Immediate technical problem:** discount amount is too large.

**Root cause:** discount responsibility is duplicated.

The root cause is more useful because it explains why the failure occurred and what design change can prevent its recurrence.

---

## 9. Hypothesis-Driven Debugging

A hypothesis should lead to an observable test.

Example:

**Hypothesis:** Input parsing is producing an incorrect number.

**Test:** Log or inspect the parsed value before the next transformation.

Another example:

**Hypothesis:** State is being unexpectedly mutated.

**Test:** Capture the state before and after the operation and compare the two snapshots.

Another example:

**Hypothesis:** An external service is responsible.

**Test:** Replace the dependency with a deterministic controlled response and compare behavior.

This approach reduces random experimentation.

---

## 10. Breakpoints

Breakpoints are most useful when the developer needs to inspect execution state interactively.

Typical breakpoint locations include:

- immediately before a suspected calculation
- immediately after an unexpected state change
- inside an exception path
- when a specific identifier is processed
- when an invariant is about to be violated

### Conditional Breakpoints

A conditional breakpoint pauses only when a specified condition is true.

For example:

`quantity < 0`

or:

`orderId == "ORD-1001"`

This prevents the debugger from stopping on every iteration of a large loop.

### Watch Expressions

A debugger can often monitor an expression rather than a single variable.

For example:

`order.total()`

or:

`cart.items.length`

This can reveal exactly when a state transition becomes incorrect.

---

## 11. Logs Versus Breakpoints

| Technique | Strength | Limitation |
|---|---|---|
| Print statements | Very simple | Easily becomes noisy |
| Logging | Persistent diagnostic context | Requires volume and data management |
| Breakpoints | Excellent interactive state inspection | Less suitable for some production failures |
| Assertions | Detect violated assumptions | Not a replacement for input validation |
| Regression tests | Repeatable verification | Cannot automatically cover every environment |
| Profiling | Identifies performance hotspots | Does not directly explain logical defects |
| Tracing | Shows execution across boundaries | Requires instrumentation |

The appropriate technique depends on the failure.

A breakpoint is useful when a developer can reproduce the issue locally.

Logs are more useful when the failure occurs in an environment that cannot be paused.

Regression tests are useful after a defect is understood because they prevent recurrence.

---

## 12. Edge Cases

Debugging should deliberately consider unusual inputs.

The implementations include examples such as:

- empty collections
- single-element collections
- duplicate values
- negative values
- invalid quantities
- invalid discounts
- invalid tax rates
- malformed numeric input
- large values
- decimal arithmetic
- asynchronous operations
- unexpected state transitions

Edge cases are important because software often behaves correctly for ordinary input while failing at boundaries.

---

## 13. Floating-Point Considerations

Binary floating-point arithmetic does not represent every decimal fraction exactly.

For example, JavaScript and Python can expose the familiar behavior where:

`0.1 + 0.2`

does not produce an exact decimal representation of `0.3`.

For financial systems, appropriate monetary representations should be considered.

Common strategies include:

- integer minor units such as cents
- decimal arithmetic libraries
- carefully controlled rounding
- database decimal types

The examples use rounding for demonstration, but production financial software requires a deliberate monetary representation strategy.

---

## 14. Exception Handling

Exception handling should distinguish between:

- detecting a failure
- providing diagnostic information
- recovering from the failure
- propagating the failure
- converting the failure into an appropriate domain-level error

A common mistake is to catch every exception and suppress it.

For example, code equivalent to:

`catch (...) {}`

can destroy important evidence.

A better approach is to handle known conditions deliberately and preserve useful diagnostic context.

---

## 15. Logging Best Practices

Good diagnostic logging should answer useful questions such as:

- What operation occurred?
- When did it occur?
- Which component produced it?
- Which request or transaction was involved?
- What relevant state was observed?
- What failure category occurred?

Poor logging often has one of two problems:

1. Too little information to diagnose the issue.
2. So much information that important events become difficult to find.

Logging should also avoid exposing sensitive information.

---

## 16. Security Considerations

Debugging data can become a security risk.

Do not log sensitive information merely because it is convenient.

Examples of data that should generally not appear in ordinary diagnostic logs include:

- passwords
- authentication tokens
- private keys
- session secrets
- complete payment-card numbers
- other confidential credentials

Useful alternatives include:

- non-sensitive identifiers
- correlation IDs
- transaction IDs
- user IDs where appropriate
- sanitized error categories
- status codes
- timing information

Production logs may be retained, copied, indexed, exported, or viewed by systems and people beyond the original development environment.

Debugging therefore requires the same care as other data-handling operations.

---

## 17. Performance Debugging

A performance problem is also a debugging problem, but performance debugging requires measurement.

Useful measurements include:

- elapsed time
- CPU usage
- memory consumption
- allocation rate
- I/O latency
- database query duration
- network latency
- cache behavior
- queue depth
- concurrency

A single timing measurement is not sufficient to explain a complex performance issue.

The C++ implementation demonstrates a simple timing measurement with `std::chrono`.

The JavaScript implementation uses `performance.now()`.

The Python implementation uses `time.perf_counter()`.

These APIs are appropriate for measuring elapsed execution time within their respective environments.

---

## 18. Complexity Considerations

The examples use simple operations where the computational cost is easy to understand.

For an order with `n` items:

- calculating a subtotal is `O(n)`
- validating each item is `O(n)`
- calculating the final discounted total is `O(n)`

The C++ performance example sums one million values:

- time complexity: `O(n)`
- stored vector space: `O(n)`

Complexity is useful during debugging because an algorithm that works correctly for 100 records may become operationally unsuitable for millions of records.

---

## 19. Debugging Mutable State

Mutable state is a common source of defects.

Examples include:

- arrays
- vectors
- maps
- caches
- object properties
- application stores
- shared configuration

A useful technique is to inspect state transitions:

`state_before -> operation -> state_after`

If an unexpected value appears, identify the earliest point where the state diverged from the expected state.

This is generally more useful than inspecting only the final failure.

---

## 20. Debugging Asynchronous Systems

Asynchronous systems introduce additional failure dimensions.

A problem may depend on:

- event ordering
- timing
- delayed responses
- timeouts
- retries
- concurrent mutations
- race conditions
- Promise rejection
- cancellation
- stale data

For these problems, diagnostic information should often include:

- timestamps
- operation identifiers
- request identifiers
- correlation identifiers
- component names
- retry counts
- status information

A failure that occurs only once in several thousand executions may require significantly more instrumentation than a deterministic local exception.

---

## 21. Debugging Distributed Systems

In a distributed architecture, a single user request may cross multiple components.

For example:

`client -> API -> authentication -> service -> database -> external service`

A failure observed by the client may originate far away from the component where the symptom becomes visible.

Correlation identifiers are therefore important.

A request identifier can connect events such as:

- request received
- validation completed
- database query started
- external service called
- external service returned
- response generated

This allows the execution path to be reconstructed after the event.

---

## 22. Debugging by Change Analysis

When a system worked previously and fails after a change, compare:

- source-code differences
- configuration differences
- dependency versions
- environment variables
- database schema
- deployment configuration
- runtime versions

A recent change is evidence, not automatic proof of causality.

The change should still be tested against the failure.

---

## 23. Minimal Reproduction

A minimal reproduction removes irrelevant complexity.

Suppose a bug occurs in a 20,000-line application.

A useful reproduction might reduce the problem to:

- one function
- one object
- one input
- one configuration value

Benefits include:

- fewer possible causes
- faster experiments
- easier reasoning
- easier regression testing
- clearer communication

A minimal reproduction is often one of the most valuable outputs of debugging.

---

## 24. Regression Testing

Once a defect has been understood, encode the failure as a test.

For example:

`calculateOrderTotal([100], 20) == 80`

The test establishes a specific expected behavior.

A regression test should ideally fail before the fix and pass after the fix.

Regression tests are especially valuable for:

- previously fixed production defects
- boundary conditions
- parsing errors
- calculation errors
- security-sensitive behavior
- compatibility behavior
- complex business rules

---

## 25. Common Debugging Mistakes

### Changing Code Before Reproducing

Without reproduction, the developer cannot easily determine whether the change affected the actual failure.

### Guessing the Root Cause

The first plausible explanation is not necessarily correct.

### Changing Multiple Things at Once

If five variables change simultaneously, it becomes difficult to know which change affected the result.

### Fixing Only the Symptom

Changing a displayed value may hide the failure while leaving the underlying defect intact.

### Ignoring Environment Differences

A failure may depend on:

- operating system
- runtime version
- configuration
- database state
- dependency version
- locale
- timezone
- permissions

### Excessive Logging

Large quantities of low-value logs can increase storage and processing costs while making important events harder to find.

### Logging Secrets

Diagnostic convenience must not override security requirements.

### Ignoring Intermittent Failures

An intermittent failure may indicate:

- race conditions
- resource contention
- timeouts
- external dependency instability
- state leakage
- ordering problems

### Failing to Add a Regression Test

Without a regression test, the same defect can return silently.

---

## 26. Assertions Versus Validation

Assertions and validation serve different purposes.

### Validation

Validation handles data that may legitimately be incorrect or untrusted.

Examples:

- user input
- API requests
- file contents
- configuration values
- external service responses

### Assertions

Assertions express assumptions that the program expects to be true internally.

For example:

`finalAmount >= 0`

after validated inputs have passed through a calculation.

An assertion is therefore an executable statement of an internal invariant.

---

## 27. Invariants

An invariant is a condition that should remain true at a particular stage of execution.

Examples:

- quantity must be positive
- discount must remain between 0 and 100
- a valid total cannot be negative
- an order identifier must exist
- a collection size cannot become negative

Invariants are powerful debugging tools because they can detect incorrect state closer to the point where it is introduced.

---

## 28. Fault Isolation

Fault isolation means narrowing the failure to a specific component or boundary.

Consider:

`input -> parser -> validator -> calculator -> formatter`

If:

- input is correct
- parser output is correct
- validator accepts the value
- calculator output is wrong

then the investigation can focus on the calculator rather than the entire application.

This dramatically reduces the search space.

---

## 29. Observability and Debugging

Observability refers to how effectively system behavior can be understood from available diagnostic information.

Useful observability signals can include:

- logs
- metrics
- traces
- error reports
- health information
- request metadata

Debugging is easier when the system exposes meaningful evidence without exposing sensitive information.

---

## 30. Production Debugging

Production debugging differs from local debugging because production systems may involve:

- real users
- sensitive data
- high traffic
- multiple services
- strict uptime requirements
- concurrency
- external dependencies
- limited ability to pause execution

Production debugging therefore often relies more heavily on:

- logs
- metrics
- traces
- controlled reproduction
- feature flags
- error reporting
- correlation IDs
- regression tests
- safe diagnostic instrumentation

Interactive breakpoints are generally more useful during local development and controlled environments than in live high-traffic systems.

---

## 31. Python, JavaScript, and C++ Comparison

| Area | Python | JavaScript | C++ |
|---|---|---|---|
| Interactive debugging | `pdb`, `breakpoint()` | `debugger`, runtime tools | Native debugger support |
| Logging | `logging` module | Console and runtime logging | Custom logger in example |
| Assertions | `assert` | `console.assert()` | `assert()` |
| Exceptions | Rich built-in hierarchy | `Error` and subclasses | Standard exception hierarchy |
| Async debugging | `asyncio` and async frameworks | Promises and `async`/`await` | Threads, futures, and other concurrency mechanisms |
| State inspection | Objects and collections | Objects, closures, runtime state | Objects, references, memory, stack |
| Performance tools | Timers and profilers | Performance APIs and profilers | Chrono, profilers, system-level tooling |
| Memory concerns | Managed memory | Garbage collection | Explicit object lifetime and resource management |
| Case-study focus | Diagnostic techniques | Runtime and asynchronous behavior | Structured system implementation |

The languages are not interchangeable in every debugging scenario.

Python emphasizes rapid experimentation and readable diagnostic code.

JavaScript requires particular attention to event-driven and asynchronous execution.

C++ exposes additional dimensions involving object lifetime, memory, compilation, resource ownership, and lower-level runtime behavior.

---

## 32. Practical Debugging Checklist

Before declaring a defect fixed, verify:

- Can the original failure be reproduced?
- Is the expected behavior explicitly defined?
- Is the actual behavior measured?
- Is the failure deterministic?
- Has the failure been minimized?
- Has the stack trace been examined?
- Have relevant variables been inspected?
- Have intermediate states been compared?
- Have hypotheses been explicitly tested?
- Has the faulty boundary been isolated?
- Has the root cause been identified?
- Does the fix address the cause?
- Has a regression test been added?
- Have related tests been executed?
- Have edge cases been tested?
- Have performance effects been considered?
- Have security implications been considered?
- Has sensitive diagnostic information been excluded?
- Has the failure been documented where operationally necessary?

---

## 33. Debugging Principles Demonstrated by the Three Programs

The three implementations collectively demonstrate several general principles.

### Reproducibility

A failure that can be reproduced can be investigated systematically.

### Observability

Useful logs and inspectable state reduce uncertainty.

### Isolation

Breaking a large operation into smaller stages narrows the search space.

### Evidence

A hypothesis becomes useful only when it can be tested against evidence.

### Invariants

Explicit assumptions help detect invalid state.

### Regression Prevention

A fixed bug should become a repeatable automated check when practical.

### Minimal Intervention

Diagnostic changes should help answer a question rather than introduce unrelated changes.

### Security Awareness

Debugging information must be treated as potentially sensitive operational data.

### Performance Awareness

Correctness and performance are separate dimensions. A program can produce correct results while using unacceptable resources.

---

## 34. Real-World Relevance

Debugging is used throughout the software lifecycle:

- local development
- unit testing
- integration testing
- staging
- deployment
- production operations
- incident response
- performance analysis
- security investigation
- maintenance
- regression prevention

The fundamental process remains similar even when the tools change:

**observe -> reproduce -> isolate -> hypothesize -> gather evidence -> identify root cause -> fix -> test -> verify**

A disciplined debugging workflow converts an unexplained failure into a sequence of testable technical questions.
