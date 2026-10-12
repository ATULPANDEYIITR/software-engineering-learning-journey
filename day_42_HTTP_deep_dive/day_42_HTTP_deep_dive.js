'use strict';

/*
 * HTTP Deep Dive: Methods, Status Codes, Headers, and Cookies
 *
 * This Node.js program focuses on JavaScript-specific HTTP behavior:
 * - IncomingMessage and ServerResponse
 * - method and URL routing
 * - request and response headers
 * - asynchronous request bodies
 * - cookies and Set-Cookie
 * - conditional requests with ETag
 * - status codes
 * - OPTIONS and CORS
 * - redirects
 * - a small stateful session model
 *
 * Run:
 *   node http-deep-dive.js
 *
 * Then open:
 *   http://127.0.0.1:8081/
 */

const http = require('node:http');
const crypto = require('node:crypto');
const { URL } = require('node:url');

const PORT = 8081;

const resources = new Map([
  [
    '42',
    {
      id: '42',
      name: 'HTTP protocol resource',
      version: 3,
      etag: '"resource-42-v3"',
    },
  ],
]);

const sessions = new Map();

const statusDescriptions = new Map([
  [200, 'Successful request'],
  [201, 'Resource created'],
  [204, 'Successful request with no response body'],
  [301, 'Permanent redirect'],
  [302, 'Temporary redirect'],
  [304, 'Cached representation is still valid'],
  [307, 'Temporary redirect preserving method'],
  [308, 'Permanent redirect preserving method'],
  [400, 'Invalid request'],
  [401, 'Authentication required'],
  [403, 'Request understood but not authorized'],
  [404, 'Resource not found'],
  [405, 'Method not allowed'],
  [409, 'Resource state conflict'],
  [412, 'Conditional request failed'],
  [415, 'Unsupported media type'],
  [422, 'Semantically invalid request'],
  [429, 'Rate limit exceeded'],
  [500, 'Internal server error'],
  [503, 'Service unavailable'],
]);

const allowedMethods = [
  'GET',
  'HEAD',
  'POST',
  'PUT',
  'PATCH',
  'DELETE',
  'OPTIONS',
];

const safeMethods = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE']);
const idempotentMethods = new Set([
  'GET',
  'HEAD',
  'OPTIONS',
  'PUT',
  'DELETE',
  'TRACE',
]);

function logStatus(code) {
  console.log(`${code}: ${statusDescriptions.get(code) ?? 'Unknown status'}`);
}

function parseCookies(header) {
  const cookies = {};

  if (!header) {
    return cookies;
  }

  for (const part of header.split(';')) {
    const separator = part.indexOf('=');

    if (separator === -1) {
      continue;
    }

    const name = part.slice(0, separator).trim();
    const value = part.slice(separator + 1).trim();

    if (name) {
      cookies[name] = decodeURIComponent(value);
    }
  }

  return cookies;
}

function serializeCookie(name, value, options = {}) {
  /*
   * Cookie attributes are response metadata. They are not sent by the
   * browser back to the server as part of the Cookie value itself.
   */
  const parts = [
    `${name}=${encodeURIComponent(value)}`,
  ];

  if (options.maxAge !== undefined) {
    parts.push(`Max-Age=${Math.floor(options.maxAge)}`);
  }

  if (options.domain) {
    parts.push(`Domain=${options.domain}`);
  }

  parts.push(`Path=${options.path ?? '/'}`);

  if (options.httpOnly) {
    parts.push('HttpOnly');
  }

  if (options.secure) {
    parts.push('Secure');
  }

  if (options.sameSite) {
    parts.push(`SameSite=${options.sameSite}`);
  }

  return parts.join('; ');
}

function createSession() {
  const sessionId = crypto.randomBytes(32).toString('base64url');

  sessions.set(sessionId, {
    user: 'developer@example.test',
    createdAt: new Date().toISOString(),
  });

  return sessionId;
}

function readSession(request) {
  const cookies = parseCookies(request.headers.cookie);
  const sessionId = cookies.session_id;

  if (!sessionId) {
    return null;
  }

  return sessions.get(sessionId) ?? null;
}

function sendJson(response, statusCode, payload, headers = {}) {
  const body = JSON.stringify(payload, null, 2);

  response.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
    ...headers,
  });

  if (statusCode !== 204) {
    response.end(body);
  } else {
    response.end();
  }
}

function sendText(response, statusCode, text, headers = {}) {
  const body = Buffer.from(text, 'utf8');

  response.writeHead(statusCode, {
    'Content-Type': 'text/plain; charset=utf-8',
    'Content-Length': body.length,
    ...headers,
  });

  response.end(body);
}

function readBody(request, maxBytes = 1_000_000) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    let settled = false;

    request.on('data', (chunk) => {
      total += chunk.length;

      if (total > maxBytes) {
        settled = true;
        reject(new Error('Request body exceeds the permitted size.'));
        request.destroy();
        return;
      }

      chunks.push(chunk);
    });

    request.on('end', () => {
      if (!settled) {
        resolve(Buffer.concat(chunks).toString('utf8'));
      }
    });

    request.on('error', (error) => {
      if (!settled) {
        reject(error);
      }
    });
  });
}

async function readJsonBody(request) {
  const contentType = request.headers['content-type'] ?? '';

  if (!contentType.toLowerCase().startsWith('application/json')) {
    const error = new Error('Content-Type must be application/json.');
    error.statusCode = 415;
    throw error;
  }

  const raw = await readBody(request);

  if (raw.trim() === '') {
    const error = new Error('JSON request body cannot be empty.');
    error.statusCode = 400;
    throw error;
  }

  try {
    return JSON.parse(raw);
  } catch {
    const error = new Error('Request body contains invalid JSON.');
    error.statusCode = 400;
    throw error;
  }
}

function negotiateContentType(acceptHeader) {
  const accepted = (acceptHeader ?? '*/*')
    .split(',')
    .map((part) => part.trim().split(';')[0].toLowerCase());

  if (accepted.includes('application/json') || accepted.includes('*/*')) {
    return 'application/json';
  }

  if (accepted.includes('text/plain')) {
    return 'text/plain';
  }

  return null;
}

function sendResource(response, request, resource) {
  const clientEtag = request.headers['if-none-match'];

  if (clientEtag && clientEtag === resource.etag) {
    response.writeHead(304, {
      ETag: resource.etag,
      'Cache-Control': 'private, max-age=60',
      Vary: 'Accept-Encoding',
    });

    response.end();
    return;
  }

  const representation = {
    id: resource.id,
    name: resource.name,
    version: resource.version,
  };

  sendJson(response, 200, representation, {
    ETag: resource.etag,
    'Cache-Control': 'private, max-age=60',
    Vary: 'Accept-Encoding',
  });
}

async function handleRequest(request, response) {
  const parsedUrl = new URL(
    request.url,
    `http://${request.headers.host ?? '127.0.0.1'}`
  );

  const method = request.method ?? 'GET';
  const path = parsedUrl.pathname;

  response.setHeader('X-Request-ID', crypto.randomUUID());

  if (method === 'OPTIONS') {
    if (path !== '/resource') {
      sendJson(response, 404, { error: 'resource_not_found' });
      return;
    }

    response.writeHead(204, {
      Allow: allowedMethods.join(', '),
      'Access-Control-Allow-Methods': allowedMethods.join(', '),
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Max-Age': '600',
      Vary: 'Origin',
    });

    response.end();
    return;
  }

  if (path === '/' && (method === 'GET' || method === 'HEAD')) {
    const accept = negotiateContentType(request.headers.accept);

    if (!accept) {
      sendJson(response, 406, {
        error: 'not_acceptable',
        supported: ['application/json', 'text/plain'],
      });
      return;
    }

    const payload = {
      service: 'HTTP Deep Dive Demo',
      methods: allowedMethods,
      endpoints: [
        '/resource',
        '/resource/42',
        '/login',
        '/me',
        '/redirect',
      ],
    };

    if (accept === 'text/plain') {
      sendText(response, 200, JSON.stringify(payload, null, 2));
    } else {
      sendJson(response, 200, payload);
    }

    return;
  }

  if (
    path === '/resource' ||
    path === '/resource/42'
  ) {
    const resource = resources.get('42');

    if (!resource) {
      sendJson(response, 404, {
        error: 'resource_not_found',
      });
      return;
    }

    if (method === 'GET' || method === 'HEAD') {
      if (method === 'HEAD') {
        const body = JSON.stringify(resource);

        response.writeHead(200, {
          'Content-Type': 'application/json; charset=utf-8',
          'Content-Length': Buffer.byteLength(body),
          ETag: resource.etag,
          'Cache-Control': 'private, max-age=60',
        });

        response.end();
        return;
      }

      sendResource(response, request, resource);
      return;
    }

    if (method === 'POST') {
      try {
        const payload = await readJsonBody(request);

        if (
          typeof payload !== 'object' ||
          payload === null ||
          Array.isArray(payload)
        ) {
          sendJson(response, 422, {
            error: 'JSON object required',
          });
          return;
        }

        if (typeof payload.name !== 'string' || payload.name.trim() === '') {
          sendJson(response, 422, {
            error: 'name is required',
          });
          return;
        }

        const newId = String(
          Math.max(...Array.from(resources.keys()).map(Number)) + 1
        );

        const newResource = {
          id: newId,
          name: payload.name.trim(),
          version: 1,
          etag: `"resource-${newId}-v1"`,
        };

        resources.set(newId, newResource);

        sendJson(response, 201, {
          created: true,
          resource: newResource,
        }, {
          Location: `/resource/${newId}`,
        });
      } catch (error) {
        sendJson(response, error.statusCode ?? 400, {
          error: error.message,
        });
      }

      return;
    }

    if (method === 'PUT') {
      try {
        const payload = await readJsonBody(request);

        if (
          typeof payload !== 'object' ||
          payload === null ||
          Array.isArray(payload)
        ) {
          sendJson(response, 422, {
            error: 'JSON object required',
          });
          return;
        }

        resource.name = String(payload.name ?? '');
        resource.version += 1;
        resource.etag = `"resource-${resource.id}-v${resource.version}"`;

        sendJson(response, 200, {
          replaced: true,
          resource,
        });
      } catch (error) {
        sendJson(response, error.statusCode ?? 400, {
          error: error.message,
        });
      }

      return;
    }

    if (method === 'PATCH') {
      try {
        const payload = await readJsonBody(request);

        if (
          typeof payload !== 'object' ||
          payload === null ||
          Array.isArray(payload)
        ) {
          sendJson(response, 422, {
            error: 'JSON object required',
          });
          return;
        }

        if (Object.hasOwn(payload, 'name')) {
          if (
            typeof payload.name !== 'string' ||
            payload.name.trim() === ''
          ) {
            sendJson(response, 422, {
              error: 'name must be a non-empty string',
            });
            return;
          }

          resource.name = payload.name.trim();
        }

        resource.version += 1;
        resource.etag = `"resource-${resource.id}-v${resource.version}"`;

        sendJson(response, 200, {
          patched: true,
          changedFields: Object.keys(payload),
          resource,
        });
      } catch (error) {
        sendJson(response, error.statusCode ?? 400, {
          error: error.message,
        });
      }

      return;
    }

    if (method === 'DELETE') {
      resources.delete(resource.id);

      response.writeHead(204, {
        'Cache-Control': 'no-store',
      });

      response.end();
      return;
    }

    response.writeHead(405, {
      Allow: allowedMethods.join(', '),
      'Content-Length': '0',
    });

    response.end();
    return;
  }

  if (path === '/login' && method === 'POST') {
    const sessionId = createSession();

    const cookie = serializeCookie(
      'session_id',
      sessionId,
      {
        httpOnly: true,
        secure: false,
        sameSite: 'Lax',
        path: '/',
        maxAge: 3600,
      }
    );

    sendJson(response, 200, {
      authenticated: true,
      user: 'developer@example.test',
    }, {
      'Set-Cookie': cookie,
    });

    return;
  }

  if (path === '/me' && (method === 'GET' || method === 'HEAD')) {
    const session = readSession(request);

    if (!session) {
      sendJson(response, 401, {
        error: 'authentication_required',
      }, {
        'WWW-Authenticate': 'Bearer realm="http-demo"',
      });

      return;
    }

    sendJson(response, 200, session);
    return;
  }

  if (path === '/logout' && method === 'POST') {
    const cookies = parseCookies(request.headers.cookie);
    const sessionId = cookies.session_id;

    if (sessionId) {
      sessions.delete(sessionId);
    }

    const deletionCookie = serializeCookie(
      'session_id',
      '',
      {
        httpOnly: true,
        secure: false,
        sameSite: 'Lax',
        path: '/',
        maxAge: 0,
      }
    );

    sendJson(response, 200, {
      authenticated: false,
    }, {
      'Set-Cookie': deletionCookie,
    });

    return;
  }

  if (path === '/redirect' && method === 'GET') {
    response.writeHead(302, {
      Location: '/',
      'Content-Length': '0',
    });

    response.end();
    return;
  }

  sendJson(response, 404, {
    error: 'resource_not_found',
    method,
    path,
  });
}

const server = http.createServer((request, response) => {
  /*
   * Node's HTTP server is event-driven. The callback receives a request and
   * response stream, while body data arrives asynchronously.
   */
  handleRequest(request, response).catch((error) => {
    console.error(error);

    if (!response.headersSent) {
      sendJson(response, 500, {
        error: 'internal_server_error',
      });
    } else {
      response.destroy();
    }
  });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`HTTP server listening on http://127.0.0.1:${PORT}`);

  console.log('\nMethod semantics:');
  for (const method of allowedMethods) {
    console.log(
      `${method.padEnd(7)} safe=${safeMethods.has(method)} ` +
      `idempotent=${idempotentMethods.has(method)}`
    );
  }

  console.log('\nStatus examples:');
  [200, 201, 204, 301, 304, 400, 401, 403, 404, 405, 409, 412, 415, 422, 429, 500, 503]
    .forEach(logStatus);

  console.log('\nTry these operations with an HTTP client:');
  console.log('GET  /resource');
  console.log('HEAD /resource');
  console.log('POST /resource');
  console.log('POST /login');
  console.log('GET  /me');
  console.log('POST /logout');
  console.log('OPTIONS /resource');
  console.log('GET /redirect');
});

process.on('SIGINT', () => {
  console.log('\nStopping HTTP server...');
  server.close(() => process.exit(0));
});
