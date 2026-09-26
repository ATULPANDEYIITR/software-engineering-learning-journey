/*
 * Documentation, README, API Documentation, and Technical Documentation
 * =======================================================================
 *
 * This self-contained JavaScript program demonstrates documentation
 * engineering through executable examples.
 *
 * Topics demonstrated:
 * - README structure
 * - API reference modeling
 * - Technical specifications
 * - Audience-driven documentation
 * - Markdown generation
 * - Documentation linting
 * - API validation
 * - Semantic versioning
 * - Changelogs
 * - Security scanning
 * - Documentation metrics
 * - Documentation testing
 * - Documentation build pipelines
 * - Browser-safe and Node.js-compatible JavaScript patterns
 *
 * Run with:
 *   node documentation_demo.js
 */

// -------------------------------------------------------------------------
// 1. DOCUMENTATION FUNDAMENTALS
// -------------------------------------------------------------------------

const documentationTypes = Object.freeze({
  README: "Project orientation and first-use information",
  API: "Machine-facing interface reference",
  TUTORIAL: "Learning-oriented guided instructions",
  HOW_TO: "Task-oriented procedure",
  REFERENCE: "Precise technical facts",
  CONCEPTUAL: "Explanations of systems and design ideas",
  TECHNICAL: "Detailed engineering documentation",
  CHANGELOG: "Versioned changes",
  RUNBOOK: "Operational procedures",
  ARCHITECTURE: "System structure and design decisions"
});

console.log("=".repeat(78));
console.log("DOCUMENTATION ENGINEERING - JAVASCRIPT");
console.log("=".repeat(78));

console.log("\nDocumentation types:");
for (const [name, purpose] of Object.entries(documentationTypes)) {
  console.log(`  ${name.padEnd(14)} -> ${purpose}`);
}


// -------------------------------------------------------------------------
// 2. STRUCTURED DOCUMENTATION OBJECTS
// -------------------------------------------------------------------------

class DocumentSection {
  constructor(title, content, level = 2) {
    if (!title || !title.trim()) {
      throw new Error("A document section requires a title.");
    }

    if (!content || !content.trim()) {
      throw new Error(`Section "${title}" requires content.`);
    }

    if (level < 1 || level > 6) {
      throw new RangeError("Markdown heading level must be between 1 and 6.");
    }

    this.title = title;
    this.content = content;
    this.level = level;
  }

  toMarkdown() {
    return `${"#".repeat(this.level)} ${this.title}\n\n${this.content.trim()}`;
  }
}


class Document {
  constructor(title, description, version = "1.0.0") {
    if (!title.trim()) {
      throw new Error("Document title cannot be empty.");
    }

    this.title = title;
    this.description = description;
    this.version = version;
    this.sections = [];
  }

  addSection(title, content, level = 2) {
    this.sections.push(new DocumentSection(title, content, level));
    return this;
  }

  toMarkdown() {
    const parts = [
      `# ${this.title}`,
      "",
      this.description.trim(),
      "",
      `**Version:** \`${this.version}\``,
      ""
    ];

    for (const section of this.sections) {
      parts.push(section.toMarkdown(), "");
    }

    return parts.join("\n").trim() + "\n";
  }
}


const readme = new Document(
  "Documentation Demo Service",
  "A small application used to demonstrate documentation engineering.",
  "1.0.0"
)
  .addSection(
    "Features",
    "- Input validation\n- Structured API contracts\n- Deterministic errors"
  )
  .addSection(
    "Installation",
    "Install dependencies and run the application with the documented command."
  )
  .addSection(
    "Usage",
    "Send a valid request to the documented endpoint."
  )
  .addSection(
    "Configuration",
    "Document configuration names, types, defaults, allowed values, and security implications."
  )
  .addSection(
    "Testing",
    "Documentation examples should be tested when practical."
  );

console.log("\nGenerated README:");
console.log(readme.toMarkdown());


// -------------------------------------------------------------------------
// 3. API DOCUMENTATION MODEL
// -------------------------------------------------------------------------

class ApiParameter {
  constructor({
    name,
    location,
    type,
    required = false,
    description,
    example = undefined
  }) {
    this.name = name;
    this.location = location;
    this.type = type;
    this.required = required;
    this.description = description;
    this.example = example;
  }
}


class ApiEndpoint {
  constructor({
    method,
    path,
    summary,
    description,
    parameters = [],
    requestBody = null,
    successStatus = 200,
    successResponse = null,
    errors = {}
  }) {
    this.method = method.toUpperCase();
    this.path = path;
    this.summary = summary;
    this.description = description;
    this.parameters = parameters;
    this.requestBody = requestBody;
    this.successStatus = successStatus;
    this.successResponse = successResponse;
    this.errors = errors;
  }

  validate() {
    const problems = [];
    const supportedMethods = [
      "GET",
      "POST",
      "PUT",
      "PATCH",
      "DELETE",
      "HEAD",
      "OPTIONS"
    ];
    const supportedLocations = [
      "path",
      "query",
      "header",
      "cookie"
    ];

    if (!supportedMethods.includes(this.method)) {
      problems.push(`Unsupported HTTP method: ${this.method}`);
    }

    if (!this.path.startsWith("/")) {
      problems.push("API path must begin with '/'.");
    }

    if (!this.summary?.trim()) {
      problems.push("API summary is missing.");
    }

    if (!this.description?.trim()) {
      problems.push("API description is missing.");
    }

    if (this.successStatus < 200 || this.successStatus >= 300) {
      problems.push("Success status must be a 2xx status.");
    }

    if (this.successResponse === null) {
      problems.push("Success response is not documented.");
    }

    const names = new Set();

    for (const parameter of this.parameters) {
      if (names.has(parameter.name)) {
        problems.push(`Duplicate parameter: ${parameter.name}`);
      }
      names.add(parameter.name);

      if (!supportedLocations.includes(parameter.location)) {
        problems.push(
          `Invalid parameter location: ${parameter.location}`
        );
      }

      if (!parameter.type?.trim()) {
        problems.push(`Missing type for ${parameter.name}`);
      }

      if (!parameter.description?.trim()) {
        problems.push(`Missing description for ${parameter.name}`);
      }

      if (parameter.required && parameter.example === undefined) {
        problems.push(
          `Required parameter ${parameter.name} has no example`
        );
      }
    }

    return problems;
  }

  toMarkdown() {
    const lines = [
      `### \`${this.method} ${this.path}\``,
      "",
      `**Summary:** ${this.summary}`,
      "",
      this.description,
      ""
    ];

    if (this.parameters.length > 0) {
      lines.push(
        "#### Parameters",
        "",
        "| Name | Location | Type | Required | Example | Description |",
        "|---|---|---|---|---|---|"
      );

      for (const parameter of this.parameters) {
        const example =
          parameter.example === undefined
            ? ""
            : String(parameter.example);

        lines.push(
          `| \`${parameter.name}\` | \`${parameter.location}\` | ` +
          `\`${parameter.type}\` | ` +
          `${parameter.required ? "Yes" : "No"} | ` +
          `\`${example}\` | ${parameter.description} |`
        );
      }

      lines.push("");
    }

    if (this.requestBody !== null) {
      lines.push(
        "#### Request Body",
        "",
        "JSON request example:",
        "",
        JSON.stringify(this.requestBody),
        ""
      );
    }

    lines.push(
      "#### Success Response",
      "",
      `HTTP status: \`${this.successStatus}\``,
      "",
      JSON.stringify(this.successResponse),
      ""
    );

    if (Object.keys(this.errors).length > 0) {
      lines.push(
        "#### Errors",
        "",
        "| Status | Meaning |",
        "|---:|---|"
      );

      for (const [status, meaning] of Object.entries(this.errors)) {
        lines.push(`| \`${status}\` | ${meaning} |`);
      }

      lines.push("");
    }

    return lines.join("\n").trim();
  }
}


const getUserEndpoint = new ApiEndpoint({
  method: "GET",
  path: "/v1/users/{id}",
  summary: "Retrieve a user",
  description:
    "Returns the user identified by the path parameter.",
  parameters: [
    new ApiParameter({
      name: "id",
      location: "path",
      type: "string",
      required: true,
      description: "Unique user identifier.",
      example: "usr_1001"
    })
  ],
  successStatus: 200,
  successResponse: {
    id: "usr_1001",
    name: "Ada Lovelace",
    email: "ada@example.com"
  },
  errors: {
    401: "Authentication is missing or invalid.",
    404: "The user does not exist."
  }
});

console.log("\nAPI validation:");
const apiErrors = getUserEndpoint.validate();

if (apiErrors.length === 0) {
  console.log("  PASS");
} else {
  for (const error of apiErrors) {
    console.log(`  ERROR: ${error}`);
  }
}

console.log("\nAPI reference:");
console.log(getUserEndpoint.toMarkdown());


// -------------------------------------------------------------------------
// 4. REQUEST VALIDATION
// -------------------------------------------------------------------------

const emailPattern =
  /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@`?/.test("")
    ? null
    : /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/;


function validateUserPayload(payload) {
  const errors = [];

  if (
    payload === null ||
    typeof payload !== "object" ||
    Array.isArray(payload)
  ) {
    return {
      valid: false,
      errors: ["Request body must be a JSON object."]
    };
  }

  if (
    typeof payload.name !== "string" ||
    payload.name.trim().length === 0
  ) {
    errors.push("name is required and must be a non-empty string.");
  }

  if (
    typeof payload.email !== "string" ||
    !emailPattern.test(payload.email)
  ) {
    errors.push("email must contain a syntactically valid email address.");
  }

  const allowedFields = new Set(["name", "email"]);

  for (const key of Object.keys(payload)) {
    if (!allowedFields.has(key)) {
      errors.push(`Unknown field: ${key}`);
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
}


const payloadExamples = [
  {
    name: "Ada Lovelace",
    email: "ada@example.com"
  },
  {
    name: "",
    email: "invalid"
  },
  {
    name: "Grace Hopper",
    email: "grace@example.com",
    role: "admin"
  }
];

console.log("\nRequest validation:");

for (const payload of payloadExamples) {
  const result = validateUserPayload(payload);

  console.log(
    `  ${JSON.stringify(payload)} -> valid=${result.valid}`
  );

  for (const error of result.errors) {
    console.log(`    - ${error}`);
  }
}


// -------------------------------------------------------------------------
// 5. DOCUMENTATION CONTRACT EXAMPLE
// -------------------------------------------------------------------------

function createUser(payload) {
  const validation = validateUserPayload(payload);

  if (!validation.valid) {
    const error = new Error(validation.errors.join("; "));
    error.code = "INVALID_REQUEST";
    error.status = 400;
    throw error;
  }

  return {
    id: "usr_demo_001",
    name: payload.name.trim(),
    email: payload.email.toLowerCase()
  };
}


console.log("\nExecutable API example:");

try {
  console.log(
    JSON.stringify(
      createUser({
        name: "Ada Lovelace",
        email: "ADA@EXAMPLE.COM"
      }),
      null,
      2
    )
  );
} catch (error) {
  console.error(error.message);
}


// -------------------------------------------------------------------------
// 6. TECHNICAL SPECIFICATION
// -------------------------------------------------------------------------

class TechnicalSpecification {
  constructor({
    problem,
    scope,
    requirements,
    architecture,
    dataFlow,
    failureModes,
    operationalNotes
  }) {
    this.problem = problem;
    this.scope = scope;
    this.requirements = requirements;
    this.architecture = architecture;
    this.dataFlow = dataFlow;
    this.failureModes = failureModes;
    this.operationalNotes = operationalNotes;
  }

  validate() {
    const errors = [];

    if (!this.problem?.trim()) {
      errors.push("Problem statement is missing.");
    }

    if (!this.scope?.trim()) {
      errors.push("Scope is missing.");
    }

    if (!Array.isArray(this.requirements) || this.requirements.length === 0) {
      errors.push("Requirements are missing.");
    }

    if (!Array.isArray(this.architecture) || this.architecture.length === 0) {
      errors.push("Architecture is missing.");
    }

    if (
      !Array.isArray(this.failureModes) ||
      this.failureModes.length === 0
    ) {
      errors.push("Failure modes are missing.");
    }

    return errors;
  }

  toMarkdown() {
    const bulletList = values =>
      values.map(value => `- ${value}`).join("\n");

    return [
      "# Technical Specification",
      "",
      "## Problem",
      "",
      this.problem,
      "",
      "## Scope",
      "",
      this.scope,
      "",
      "## Requirements",
      "",
      bulletList(this.requirements),
      "",
      "## Architecture",
      "",
      bulletList(this.architecture),
      "",
      "## Data Flow",
      "",
      bulletList(this.dataFlow),
      "",
      "## Failure Modes",
      "",
      bulletList(this.failureModes),
      "",
      "## Operational Notes",
      "",
      bulletList(this.operationalNotes)
    ].join("\n");
  }
}


const specification = new TechnicalSpecification({
  problem:
    "Provide a stable documented contract for creating user resources.",
  scope:
    "The system accepts JSON requests and produces structured JSON responses.",
  requirements: [
    "Validate request fields.",
    "Return predictable status categories.",
    "Document authentication requirements.",
    "Avoid leaking internal errors."
  ],
  architecture: [
    "HTTP interface",
    "Validation layer",
    "Application service",
    "Persistence abstraction",
    "Response serializer"
  ],
  dataFlow: [
    "Client request",
    "Parsing",
    "Validation",
    "Application logic",
    "Response serialization"
  ],
  failureModes: [
    "Malformed input",
    "Validation failure",
    "Duplicate resource",
    "Unexpected internal error"
  ],
  operationalNotes: [
    "Use structured logs.",
    "Monitor error rates and latency.",
    "Protect secrets with a secret-management system."
  ]
});

console.log("\nTechnical specification validation:");
console.log(
  specification.validate().length === 0 ? "  PASS" : "  FAIL"
);


// -------------------------------------------------------------------------
// 7. MARKDOWN LINTING
// -------------------------------------------------------------------------

function validateMarkdown(markdown) {
  const problems = [];

  if (!markdown.trim()) {
    problems.push("Document is empty.");
    return problems;
  }

  if (!/^#\s+\S+/m.test(markdown)) {
    problems.push("Missing level-one heading.");
  }

  const fenceCount = (markdown.match(/```/g) || []).length;

  if (fenceCount % 2 !== 0) {
    problems.push("Unbalanced Markdown code fences.");
  }

  const links = [...markdown.matchAll(/\[([^\]]+)\]\(([^)]+)\)/g)];

  for (const match of links) {
    const label = match[1];
    const target = match[2];

    if (!label.trim()) {
      problems.push("Link has empty label.");
    }

    if (!target.trim()) {
      problems.push(`Link "${label}" has empty target.`);
    }
  }

  return problems;
}


const markdownSample = `
# API Guide

## Authentication

Requests require authentication.

## Endpoint

Use \`POST /v1/users\`.

[API reference](./api.md)
`;

console.log("\nMarkdown linting:");

const markdownErrors = validateMarkdown(markdownSample);

if (markdownErrors.length === 0) {
  console.log("  PASS");
} else {
  for (const error of markdownErrors) {
    console.log(`  ERROR: ${error}`);
  }
}


// -------------------------------------------------------------------------
// 8. DOCUMENTATION METRICS
// -------------------------------------------------------------------------

function documentationMetrics(markdown, requiredSections = []) {
  const headings = [
    ...markdown.matchAll(/^#{1,6}\s+(.+)$/gm)
  ].map(match => match[1].trim());

  const required = new Set(
    requiredSections.map(section => section.toLowerCase())
  );

  const present = new Set(
    headings.map(heading => heading.toLowerCase())
  );

  let sectionCoverage = 1;

  if (required.size > 0) {
    let matched = 0;

    for (const section of required) {
      if (present.has(section)) {
        matched += 1;
      }
    }

    sectionCoverage = matched / required.size;
  }

  return {
    characters: markdown.length,
    lines: markdown.split("\n").length,
    words: markdown.trim() ? markdown.trim().split(/\s+/).length : 0,
    headings: headings.length,
    links: [...markdown.matchAll(/\[[^\]]+\]\([^)]+\)/g)].length,
    sectionCoverage
  };
}


console.log("\nDocumentation metrics:");
console.log(
  documentationMetrics(readme.toMarkdown(), [
    "Features",
    "Installation",
    "Usage",
    "Configuration",
    "Testing"
  ])
);


// -------------------------------------------------------------------------
// 9. SEMANTIC VERSIONING
// -------------------------------------------------------------------------

function classifyVersionChange(oldVersion, newVersion) {
  if (newVersion.major !== oldVersion.major) {
    return "potentially breaking / major contract change";
  }

  if (newVersion.minor !== oldVersion.minor) {
    return "backward-compatible feature change";
  }

  if (newVersion.patch !== oldVersion.patch) {
    return "backward-compatible correction";
  }

  return "no version change";
}


const versionChanges = [
  [[1, 4, 2], [1, 4, 3]],
  [[1, 4, 2], [1, 5, 0]],
  [[1, 4, 2], [2, 0, 0]]
];

console.log("\nVersioning:");
for (const [oldVersion, newVersion] of versionChanges) {
  console.log(
    `  ${oldVersion.join(".")} -> ${newVersion.join(".")}: ` +
    classifyVersionChange(
      {
        major: oldVersion[0],
        minor: oldVersion[1],
        patch: oldVersion[2]
      },
      {
        major: newVersion[0],
        minor: newVersion[1],
        patch: newVersion[2]
      }
    )
  );
}


// -------------------------------------------------------------------------
// 10. CHANGELOG
// -------------------------------------------------------------------------

function renderChangelog(version, changes) {
  const groups = new Map();

  for (const change of changes) {
    if (!groups.has(change.category)) {
      groups.set(change.category, []);
    }

    groups.get(change.category).push(change);
  }

  const lines = [`## [${version}]`, ""];

  for (const category of [...groups.keys()].sort()) {
    lines.push(`### ${category}`, "");

    for (const change of groups.get(category)) {
      const issue = change.issue ? ` (${change.issue})` : "";
      lines.push(`- ${change.description}${issue}`);
    }

    lines.push("");
  }

  return lines.join("\n").trim();
}


console.log("\nChangelog:");

console.log(
  renderChangelog("1.5.0", [
    {
      category: "Added",
      description: "Documented user creation endpoint",
      issue: "#101"
    },
    {
      category: "Changed",
      description: "Clarified validation rules",
      issue: "#102"
    },
    {
      category: "Fixed",
      description: "Corrected duplicate-user error documentation",
      issue: "#103"
    }
  ])
);


// -------------------------------------------------------------------------
// 11. SECURITY DOCUMENTATION SCANNING
// -------------------------------------------------------------------------

const secretPatterns = [
  /\b(?:api[_-]?key|secret|password|token)\s*[:=]\s*\S+/gi,
  /\bsk-[A-Za-z0-9_-]{12,}\b/g
];


function findPossibleSecrets(text) {
  const findings = [];

  for (const pattern of secretPatterns) {
    const matches = text.match(pattern) || [];
    findings.push(...matches);
  }

  return findings;
}


const unsafeDocumentation = `
# Configuration

api_key = sk-example-secret-value
`;

console.log("\nSecurity scan:");

const findings = findPossibleSecrets(unsafeDocumentation);

if (findings.length === 0) {
  console.log("  PASS");
} else {
  for (const finding of findings) {
    console.log(`  POTENTIAL SECRET: ${finding}`);
  }
}


// -------------------------------------------------------------------------
// 12. API CONTRACT REPRESENTATION
// -------------------------------------------------------------------------

const apiContract = {
  openapi: "3.0.3",
  info: {
    title: "Documentation Demo API",
    version: "1.0.0"
  },
  paths: {
    "/v1/users": {
      post: {
        summary: "Create a user",
        requestBody: {
          required: true,
          content: {
            "application/json": {
              schema: {
                type: "object",
                required: ["name", "email"],
                properties: {
                  name: {
                    type: "string"
                  },
                  email: {
                    type: "string",
                    format: "email"
                  }
                }
              }
            }
          }
        },
        responses: {
          "201": {
            description: "User created"
          },
          "400": {
            description: "Invalid request"
          },
          "409": {
            description: "Duplicate user"
          }
        }
      }
    }
  }
};

console.log("\nAPI contract:");
console.log(JSON.stringify(apiContract, null, 2));


// -------------------------------------------------------------------------
// 13. DOCUMENTATION CONSISTENCY CHECKING
// -------------------------------------------------------------------------

function extractApiPaths(markdown) {
  const matches = [
    ...markdown.matchAll(
      /`(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+([^`\s]+)`/g
    )
  ];

  return [...new Set(matches.map(match => match[1]))];
}


const apiMarkdown = `
# API Reference

Use \`POST /v1/users\` to create a user.

Use \`GET /v1/users/{id}\` to retrieve a user.
`;

console.log("\nDocumented API paths:");

for (const path of extractApiPaths(apiMarkdown).sort()) {
  console.log(`  - ${path}`);
}


// -------------------------------------------------------------------------
// 14. DOCUMENTATION STRUCTURE DIFF
// -------------------------------------------------------------------------

function extractHeadings(markdown) {
  return new Set(
    [...markdown.matchAll(/^#{1,6}\s+(.+)$/gm)]
      .map(match => match[1].trim())
  );
}


function compareDocumentation(oldMarkdown, newMarkdown) {
  const oldHeadings = extractHeadings(oldMarkdown);
  const newHeadings = extractHeadings(newMarkdown);

  const added = [];
  const removed = [];

  for (const heading of newHeadings) {
    if (!oldHeadings.has(heading)) {
      added.push(heading);
    }
  }

  for (const heading of oldHeadings) {
    if (!newHeadings.has(heading)) {
      removed.push(heading);
    }
  }

  return {
    addedHeadings: added,
    removedHeadings: removed
  };
}


const oldDocumentation = `
# API
## Authentication
## Users
`;

const newDocumentation = `
# API
## Authentication
## Users
## Pagination
`;

console.log("\nDocumentation structure diff:");
console.log(
  compareDocumentation(oldDocumentation, newDocumentation)
);


// -------------------------------------------------------------------------
// 15. ERROR REFERENCE
// -------------------------------------------------------------------------

const errorDefinitions = [
  {
    code: "INVALID_REQUEST",
    status: 400,
    meaning: "The request cannot be parsed or validated.",
    resolution: "Correct the request according to the documented schema."
  },
  {
    code: "UNAUTHORIZED",
    status: 401,
    meaning: "Authentication credentials are missing or invalid.",
    resolution: "Provide valid authentication credentials."
  },
  {
    code: "NOT_FOUND",
    status: 404,
    meaning: "The requested resource does not exist.",
    resolution: "Verify the resource identifier."
  },
  {
    code: "CONFLICT",
    status: 409,
    meaning: "The operation conflicts with current resource state.",
    resolution: "Refresh resource state before retrying when appropriate."
  },
  {
    code: "INTERNAL_ERROR",
    status: 500,
    meaning: "The server encountered an unexpected condition.",
    resolution: "Use the documented correlation identifier for support."
  }
];

console.log("\nError reference:");

for (const error of errorDefinitions) {
  console.log(
    `  ${error.code} (${error.status}) -> ` +
    `${error.meaning} | ${error.resolution}`
  );
}


// -------------------------------------------------------------------------
// 16. AUDIENCE-DRIVEN DOCUMENTATION
// -------------------------------------------------------------------------

const audiences = [
  {
    name: "End user",
    question: "How do I complete the task?",
    style: "Task-oriented"
  },
  {
    name: "Developer",
    question: "How do I integrate or modify it?",
    style: "Technical reference"
  },
  {
    name: "Operator",
    question: "How do I run and recover it?",
    style: "Operational"
  },
  {
    name: "Architect",
    question: "Why is the system designed this way?",
    style: "Conceptual and architectural"
  },
  {
    name: "Maintainer",
    question: "How do I keep docs synchronized with code?",
    style: "Detailed engineering"
  }
];

console.log("\nAudience mapping:");

for (const audience of audiences) {
  console.log(
    `  ${audience.name}: ${audience.question} [${audience.style}]`
  );
}


// -------------------------------------------------------------------------
// 17. DOCUMENTATION TESTING
// -------------------------------------------------------------------------

function assert(condition, message) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}


function runDocumentationTests() {
  const validPayload = validateUserPayload({
    name: "Ada Lovelace",
    email: "ada@example.com"
  });

  assert(validPayload.valid, "Valid user payload should pass.");

  const invalidPayload = validateUserPayload({
    name: "",
    email: "bad"
  });

  assert(
    !invalidPayload.valid,
    "Invalid user payload should fail."
  );

  assert(
    getUserEndpoint.validate().length === 0,
    "API documentation should be structurally complete."
  );

  assert(
    validateMarkdown(readme.toMarkdown()).length === 0,
    "Generated README should pass basic linting."
  );

  assert(
    classifyVersionChange(
      { major: 1, minor: 0, patch: 0 },
      { major: 1, minor: 1, patch: 0 }
    ) === "backward-compatible feature change",
    "Minor version should represent a compatible feature change."
  );

  return true;
}


console.log("\nDocumentation tests:");

try {
  runDocumentationTests();
  console.log("  PASS: all tests passed");
} catch (error) {
  console.log(`  FAIL: ${error.message}`);
}


// -------------------------------------------------------------------------
// 18. BROWSER-SIDE DOCUMENTATION INDEX
// -------------------------------------------------------------------------

function createDocumentationIndex(entries) {
  /*
   * This function is browser-compatible because it does not require Node.js
   * APIs. A web documentation site can use the resulting object to construct
   * navigation, search indexes, or cards.
   */

  return entries
    .filter(entry =>
      entry &&
      typeof entry.title === "string" &&
      typeof entry.path === "string"
    )
    .map(entry => ({
      title: entry.title.trim(),
      path: entry.path.trim(),
      category: entry.category?.trim() || "General"
    }));
}


const documentationIndex = createDocumentationIndex([
  {
    title: "Getting Started",
    path: "/docs/getting-started",
    category: "Tutorial"
  },
  {
    title: "Authentication",
    path: "/docs/authentication",
    category: "How-to"
  },
  {
    title: "API Reference",
    path: "/docs/api",
    category: "Reference"
  },
  {
    title: "Architecture",
    path: "/docs/architecture",
    category: "Conceptual"
  }
]);

console.log("\nDocumentation index:");
console.table(documentationIndex);


// -------------------------------------------------------------------------
// 19. SEARCH-ORIENTED DOCUMENTATION
// -------------------------------------------------------------------------

function tokenizeForSearch(text) {
  return text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(/\s+/)
    .filter(Boolean);
}


function searchDocumentation(documents, query) {
  const queryTerms = new Set(tokenizeForSearch(query));

  return documents
    .map(document => {
      const terms = tokenizeForSearch(
        `${document.title} ${document.content}`
      );

      const termSet = new Set(terms);

      let score = 0;

      for (const queryTerm of queryTerms) {
        if (termSet.has(queryTerm)) {
          score += 1;
        }
      }

      return {
        ...document,
        score
      };
    })
    .filter(document => document.score > 0)
    .sort((a, b) => b.score - a.score);
}


const searchableDocuments = [
  {
    title: "Authentication",
    content:
      "Configure API authentication with bearer credentials."
  },
  {
    title: "Pagination",
    content:
      "Use page and limit parameters when retrieving collections."
  },
  {
    title: "Error Handling",
    content:
      "Review documented HTTP error responses and recovery behavior."
  }
];

console.log("\nDocumentation search:");

console.table(
  searchDocumentation(searchableDocuments, "API authentication")
);


// -------------------------------------------------------------------------
// 20. PRODUCTION DOCUMENTATION PIPELINE
// -------------------------------------------------------------------------

class DocumentationPipeline {
  constructor() {
    this.stages = [
      "Load source",
      "Lint structure",
      "Validate examples",
      "Check links",
      "Scan for secrets",
      "Generate output",
      "Publish"
    ];
  }

  run(markdown) {
    const results = [];

    const lintErrors = validateMarkdown(markdown);

    results.push({
      stage: "Lint structure",
      passed: lintErrors.length === 0,
      details: lintErrors
    });

    const securityFindings = findPossibleSecrets(markdown);

    results.push({
      stage: "Scan for secrets",
      passed: securityFindings.length === 0,
      details: securityFindings
    });

    const allPassed = results.every(result => result.passed);

    return {
      passed: allPassed,
      results
    };
  }
}


const pipeline = new DocumentationPipeline();
const pipelineResult = pipeline.run(readme.toMarkdown());

console.log("\nDocumentation pipeline:");

for (const result of pipelineResult.results) {
  console.log(
    `  ${result.passed ? "PASS" : "FAIL"}: ${result.stage}`
  );

  for (const detail of result.details) {
    console.log(`    - ${detail}`);
  }
}

console.log(
  `  Final status: ${pipelineResult.passed ? "PUBLISHABLE" : "BLOCKED"}`
);


// -------------------------------------------------------------------------
// 21. TECHNICAL TRADE-OFFS
// -------------------------------------------------------------------------

const tradeOffs = [
  {
    decision: "Generated API reference",
    benefit: "Reduces duplication between machine-readable contracts and reference pages.",
    cost: "Generated output cannot replace human explanation of rationale and workflows."
  },
  {
    decision: "Single large README",
    benefit: "Easy to find in a repository.",
    cost: "Becomes difficult to scan as project complexity increases."
  },
  {
    decision: "Multiple focused documents",
    benefit: "Better separation of tutorials, procedures, concepts, and reference material.",
    cost: "Requires strong navigation and information architecture."
  },
  {
    decision: "Executable examples",
    benefit: "Examples can detect implementation drift.",
    cost: "Examples become test-maintenance responsibilities."
  }
];

console.log("\nDocumentation trade-offs:");

for (const tradeOff of tradeOffs) {
  console.log(`\n  ${tradeOff.decision}`);
  console.log(`    Benefit: ${tradeOff.benefit}`);
  console.log(`    Cost: ${tradeOff.cost}`);
}


// -------------------------------------------------------------------------
// 22. FINAL DOCUMENT GENERATION
// -------------------------------------------------------------------------

const finalDocument = new Document(
  "User Creation API",
  "Reference documentation for a versioned user-creation endpoint.",
  "1.0.0"
)
  .addSection(
    "Purpose",
    "Creates a user resource after validating the supplied identity fields."
  )
  .addSection(
    "Authentication",
    "Requests require valid authentication. Credentials must never be stored in public examples."
  )
  .addSection(
    "Endpoint",
    getUserEndpoint.toMarkdown()
  )
  .addSection(
    "Validation Rules",
    "- `id` identifies a resource.\n" +
    "- Request fields must conform to the documented schema.\n" +
    "- Unknown fields are rejected by the demonstrated contract."
  )
  .addSection(
    "Failure Behavior",
    "- `400`: invalid request.\n" +
    "- `401`: authentication failure.\n" +
    "- `404`: resource not found.\n" +
    "- `500`: unexpected server error."
  )
  .addSection(
    "Operational Notes",
    "Production systems should document logging, monitoring, rate limits, retry behavior, authorization, secret management, and incident procedures."
  );

console.log("\nComplete generated technical document:");
console.log("-".repeat(78));
console.log(finalDocument.toMarkdown());

console.log("=".repeat(78));
console.log("DOCUMENTATION STUDY PROGRAM COMPLETE");
console.log("=".repeat(78));
