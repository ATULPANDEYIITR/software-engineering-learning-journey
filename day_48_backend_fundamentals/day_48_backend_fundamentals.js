"use strict";

/*
 * Backend fundamentals through a Node.js HTTP application.
 *
 * This file intentionally uses Node's standard-library http module rather
 * than Express so that server creation, routing, middleware composition,
 * request streaming, response construction, and asynchronous control flow
 * remain visible.
 */

const http = require("node:http");
const { URL } = require("node:url");
const crypto = require("node:crypto");

const PORT = Number(process.env.PORT || 8080);
const HOST = process.env.HOST || "127.0.0.1";
const MAX_BODY_BYTES = 1024 * 1024;

class HttpError extends Error {
  constructor(status, code, message, headers = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.headers = headers;
  }
}

function jsonResponse(res, status, payload, headers = {}) {
  const body = JSON.stringify(payload);

  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    ...headers,
  });

  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let totalBytes = 0;

    req.on("data", (chunk) => {
      totalBytes += chunk.length;

      if (totalBytes > MAX_BODY_BYTES) {
        reject(
          new HttpError(
            413,
            "payload_too_large",
            "Request body exceeds the configured limit."
          )
        );

        req.destroy();
        return;
      }

      chunks.push(chunk);
    });

    req.on("end", () => {
      resolve(Buffer.concat(chunks));
    });

    req.on("error", reject);
  });
}

async function parseJsonBody(req) {
  const body = await readBody(req);

  if (body.length === 0) {
    return null;
  }

  const contentType = String(req.headers["content-type"] || "");

  if (!contentType.toLowerCase().includes("application/json")) {
    throw new HttpError(
      415,
      "unsupported_media_type",
      "This endpoint requires application/json."
    );
  }

  try {
    return JSON.parse(body.toString("utf8"));
  } catch {
    throw new HttpError(
      400,
      "invalid_json",
      "The request body contains invalid JSON."
    );
  }
}

class Router {
  constructor() {
    this.routes = [];
  }

  add(method, pattern, handler) {
    const segments = pattern.split("/").filter(Boolean);

    const parameterNames = [];
    const expressionSegments = segments.map((segment) => {
      if (segment.startsWith(":")) {
        parameterNames.push(segment.slice(1));
        return "([^/]+)";
      }

      return segment.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    });

    const regex =
      pattern === "/"
        ? /^\/$/
        : new RegExp(`^/${expressionSegments.join("/")}/?$`);

    this.routes.push({
      method: method.toUpperCase(),
      pattern,
      regex,
      parameterNames,
      handler,
      staticSegments: segments.filter(
        (segment) => !segment.startsWith(":")
      ).length,
    });
  }

  get(pattern, handler) {
    this.add("GET", pattern, handler);
  }

  post(pattern, handler) {
    this.add("POST", pattern, handler);
  }

  delete(pattern, handler) {
    this.add("DELETE", pattern, handler);
  }

  match(method, pathname) {
    const candidates = this.routes
      .filter((route) => route.method === method.toUpperCase())
      .sort((a, b) => b.staticSegments - a.staticSegments);

    for (const route of candidates) {
      const match = route.regex.exec(pathname);

      if (match) {
        const params = {};

        route.parameterNames.forEach((name, index) => {
          params[name] = decodeURIComponent(match[index + 1]);
        });

        return {
          handler: route.handler,
          params,
        };
      }
    }

    return null;
  }

  allowedMethods(pathname) {
    return this.routes
      .filter((route) => route.regex.test(pathname))
      .map((route) => route.method)
      .filter((method, index, methods) => methods.indexOf(method) === index)
      .sort()
      .join(", ");
  }
}

/*
 * Middleware is represented as a function that receives the next handler.
 * The returned function controls whether and when downstream processing
 * occurs. This is the same onion-style execution model used by many
 * production backend frameworks.
 */
function compose(middlewares, finalHandler) {
  return middlewares.reduceRight(
    (next, middleware) => middleware(next),
    finalHandler
  );
}

function requestIdMiddleware(next) {
  return async (ctx) => {
    const supplied = String(ctx.req.headers["x-request-id"] || "");

    ctx.requestId =
      supplied.length > 0 && supplied.length <= 80
        ? supplied
        : crypto.randomUUID();

    const response = await next(ctx);
    response.headers["X-Request-ID"] = ctx.requestId;
    return response;
  };
}

function loggingMiddleware(next) {
  return async (ctx) => {
    const started = process.hrtime.bigint();

    try {
      const response = await next(ctx);

      const elapsedMs =
        Number(process.hrtime.bigint() - started) / 1_000_000;

      console.log(
        `${ctx.req.method} ${ctx.url.pathname} -> ${response.status} ` +
          `${elapsedMs.toFixed(2)}ms requestId=${ctx.requestId}`
      );

      return response;
    } catch (error) {
      const elapsedMs =
        Number(process.hrtime.bigint() - started) / 1_000_000;

      console.error(
        `${ctx.req.method} ${ctx.url.pathname} -> error ` +
          `${elapsedMs.toFixed(2)}ms requestId=${ctx.requestId}`
      );

      throw error;
    }
  };
}

function authenticationMiddleware(next) {
  return async (ctx) => {
    const authorization = String(
      ctx.req.headers.authorization || ""
    );

    if (authorization === "Bearer demo-admin-token") {
      ctx.user = {
        id: "admin-1",
        role: "admin",
      };
    } else if (authorization === "Bearer demo-user-token") {
      ctx.user = {
        id: "user-1",
        role: "user",
      };
    } else {
      throw new HttpError(
        401,
        "unauthorized",
        "A valid bearer token is required.",
        {
          "WWW-Authenticate": "Bearer",
        }
      );
    }

    return next(ctx);
  };
}

function requireRole(role) {
  return (next) => async (ctx) => {
    if (!ctx.user || ctx.user.role !== role) {
      throw new HttpError(
        403,
        "forbidden",
        `The ${role} role is required.`
      );
    }

    return next(ctx);
  };
}

const users = new Map([
  [
    "1001",
    {
      id: "1001",
      name: "Asha Sharma",
      role: "engineer",
    },
  ],
  [
    "1002",
    {
      id: "1002",
      name: "Ravi Mehta",
      role: "reviewer",
    },
  ],
]);

const router = new Router();

router.get("/health", async () => ({
  status: 200,
  body: {
    status: "healthy",
    service: "node-backend-fundamentals",
    uptimeSeconds: process.uptime(),
  },
  headers: {},
}));

router.get("/users", async (ctx) => {
  const role = ctx.url.searchParams.get("role");

  const result = [...users.values()].filter(
    (user) => !role || user.role === role
  );

  return {
    status: 200,
    body: {
      count: result.length,
      users: result,
    },
    headers: {},
  };
});

router.get("/users/:id", async (ctx) => {
  const user = users.get(ctx.params.id);

  if (!user) {
    throw new HttpError(
      404,
      "user_not_found",
      `No user exists with ID ${ctx.params.id}.`
    );
  }

  return {
    status: 200,
    body: user,
    headers: {},
  };
});

const createUser = async (ctx) => {
  const payload = await parseJsonBody(ctx.req);

  if (
    !payload ||
    typeof payload !== "object" ||
    Array.isArray(payload)
  ) {
    throw new HttpError(
      400,
      "invalid_payload",
      "The JSON payload must be an object."
    );
  }

  const name = String(payload.name || "").trim();
  const role = String(payload.role || "").trim();

  if (!name || name.length > 100) {
    throw new HttpError(
      400,
      "invalid_name",
      "name must contain between 1 and 100 characters."
    );
  }

  if (!["engineer", "reviewer", "admin"].includes(role)) {
    throw new HttpError(
      400,
      "invalid_role",
      "role must be engineer, reviewer, or admin."
    );
  }

  const numericIds = [...users.keys()].map(Number);
  const id = String(Math.max(...numericIds, 1000) + 1);

  const user = {
    id,
    name,
    role,
  };

  users.set(id, user);

  return {
    status: 201,
    body: user,
    headers: {
      Location: `/users/${id}`,
    },
  };
};

const createUserProtected = compose(
  [authenticationMiddleware, requireRole("admin")],
  createUser
);

router.post("/users", createUserProtected);

router.delete(
  "/users/:id",
  compose(
    [authenticationMiddleware, requireRole("admin")],
    async (ctx) => {
      if (!users.has(ctx.params.id)) {
        throw new HttpError(
          404,
          "user_not_found",
          "The requested user does not exist."
        );
      }

      users.delete(ctx.params.id);

      return {
        status: 204,
        body: null,
        headers: {},
      };
    }
  )
);

async function dispatch(ctx) {
  const matched = router.match(ctx.req.method, ctx.url.pathname);

  if (!matched) {
    const allowed = router.allowedMethods(ctx.url.pathname);

    if (allowed) {
      throw new HttpError(
        405,
        "method_not_allowed",
        `Method ${ctx.req.method} is not supported.`,
        {
          Allow: allowed,
        }
      );
    }

    throw new HttpError(
      404,
      "not_found",
      `No route matches ${ctx.req.method} ${ctx.url.pathname}.`
    );
  }

  ctx.params = matched.params;
  return matched.handler(ctx);
}

const application = compose(
  [requestIdMiddleware, loggingMiddleware],
  dispatch
);

const server = http.createServer(async (req, res) => {
  const url = new URL(
    req.url || "/",
    `http://${req.headers.host || `${HOST}:${PORT}`}`
  );

  const context = {
    req,
    res,
    url,
    requestId: null,
    user: null,
    params: {},
  };

  try {
    const result = await application(context);

    if (result.status === 204) {
      res.writeHead(204, result.headers);
      res.end();
      return;
    }

    jsonResponse(
      res,
      result.status,
      result.body,
      result.headers
    );
  } catch (error) {
    if (error instanceof HttpError) {
      jsonResponse(
        res,
        error.status,
        {
          error: error.code,
          message: error.message,
          requestId: context.requestId,
        },
        error.headers
      );
      return;
    }

    console.error("Unhandled server error:", error);

    jsonResponse(
      res,
      500,
      {
        error: "internal_server_error",
        message: "The server could not complete the request.",
        requestId: context.requestId,
      }
    );
  }
});

server.listen(PORT, HOST, () => {
  console.log(`Server listening at http://${HOST}:${PORT}`);
  console.log("GET    /health");
  console.log("GET    /users");
  console.log("GET    /users/:id");
  console.log("POST   /users");
  console.log("DELETE /users/:id");
});

function shutdown(signal) {
  console.log(`${signal} received; stopping new connections.`);

  server.close((error) => {
    if (error) {
      console.error("Graceful shutdown failed:", error);
      process.exitCode = 1;
      return;
    }

    console.log("HTTP server stopped.");
  });
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
