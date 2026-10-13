'use strict';

/*
 * REST API DESIGN LAB
 *
 * Node.js standard-library implementation focused on:
 * - resource-oriented URI design
 * - API versioning
 * - HTTP method semantics
 * - pagination
 * - filtering
 * - validation
 * - structured errors
 * - event-driven lifecycle processing
 * - conditional merge of API policy decisions
 *
 * Run with:
 *   node rest_api_design.js
 */

const http = require('node:http');
const { URL } = require('node:url');

const HOST = '127.0.0.1';
const PORT = 8081;
const API_VERSION = 'v1';

const books = new Map([
  [1, {
    id: 1,
    title: 'Designing Data-Intensive Applications',
    author: 'Martin Kleppmann',
    category: 'distributed-systems',
    publishedYear: 2017
  }],
  [2, {
    id: 2,
    title: 'Clean Architecture',
    author: 'Robert C. Martin',
    category: 'software-engineering',
    publishedYear: 2017
  }],
  [3, {
    id: 3,
    title: 'HTTP: The Definitive Guide',
    author: 'David Gourley',
    category: 'web',
    publishedYear: 2002
  }],
  [4, {
    id: 4,
    title: 'Building Microservices',
    author: 'Sam Newman',
    category: 'architecture',
    publishedYear: 2021
  }],
  [5, {
    id: 5,
    title: 'API Design Patterns',
    author: 'JJ Geewax',
    category: 'api-design',
    publishedYear: 2021
  }]
]);

let nextBookId = 6;

class ApiError extends Error {
  constructor(status, code, message, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function sendJson(response, status, payload, headers = {}) {
  const body = JSON.stringify(payload, null, 2);

  response.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
    ...headers
  });

  response.end(body);
}

function sendError(response, error) {
  if (error instanceof ApiError) {
    sendJson(response, error.status, {
      error: {
        code: error.code,
        message: error.message,
        details: error.details
      }
    });
    return;
  }

  console.error(error);

  sendJson(response, 500, {
    error: {
      code: 'internal_error',
      message: 'An unexpected server error occurred.'
    }
  });
}

function parsePositiveInteger(value, name, defaultValue) {
  if (value === null || value === '') {
    return defaultValue;
  }

  if (!/^\d+$/.test(value)) {
    throw new ApiError(
      400,
      'invalid_parameter',
      `${name} must be a positive integer.`
    );
  }

  const parsed = Number(value);

  if (!Number.isSafeInteger(parsed) || parsed < 1) {
    throw new ApiError(
      400,
      'invalid_parameter',
      `${name} must be a positive integer.`
    );
  }

  return parsed;
}

function validateBookPayload(payload) {
  if (
    payload === null ||
    typeof payload !== 'object' ||
    Array.isArray(payload)
  ) {
    throw new ApiError(
      400,
      'invalid_body',
      'The request body must be a JSON object.'
    );
  }

  const required = ['title', 'author', 'category', 'publishedYear'];
  const missing = required.filter(
    field => !(field in payload)
  );

  if (missing.length > 0) {
    throw new ApiError(
      400,
      'validation_error',
      'Required fields are missing.',
      { missing }
    );
  }

  for (const field of ['title', 'author', 'category']) {
    if (
      typeof payload[field] !== 'string' ||
      payload[field].trim().length === 0
    ) {
      throw new ApiError(
        400,
        'validation_error',
        `${field} must be a non-empty string.`
      );
    }
  }

  if (
    !Number.isInteger(payload.publishedYear) ||
    payload.publishedYear < 1000 ||
    payload.publishedYear > new Date().getUTCFullYear()
  ) {
    throw new ApiError(
      422,
      'invalid_published_year',
      'publishedYear is outside the supported range.'
    );
  }
}

async function readJsonBody(request) {
  const chunks = [];
  let totalBytes = 0;
  const maximumBodySize = 1_000_000;

  for await (const chunk of request) {
    totalBytes += chunk.length;

    if (totalBytes > maximumBodySize) {
      throw new ApiError(
        413,
        'payload_too_large',
        'Request body exceeds the 1 MB limit.'
      );
    }

    chunks.push(chunk);
  }

  if (chunks.length === 0) {
    throw new ApiError(
      400,
      'empty_body',
      'A JSON request body is required.'
    );
  }

  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    throw new ApiError(
      400,
      'invalid_json',
      'Request body contains invalid JSON.'
    );
  }
}

function buildPagination(items, page, pageSize, path) {
  const totalItems = items.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const start = (page - 1) * pageSize;
  const data = items.slice(start, start + pageSize);

  const links = {
    self: `${path}?page=${page}&page_size=${pageSize}`,
    first: `${path}?page=1&page_size=${pageSize}`
  };

  if (page > 1 && totalPages > 0) {
    links.previous =
      `${path}?page=${page - 1}&page_size=${pageSize}`;
  }

  if (page < totalPages) {
    links.next =
      `${path}?page=${page + 1}&page_size=${pageSize}`;
  }

  if (totalPages > 0) {
    links.last =
      `${path}?page=${totalPages}&page_size=${pageSize}`;
  }

  return {
    data,
    pagination: {
      page,
      pageSize,
      totalItems,
      totalPages,
      hasPrevious: page > 1 && totalItems > 0,
      hasNext: page < totalPages
    },
    links
  };
}

function listBooks(url) {
  const page = parsePositiveInteger(
    url.searchParams.get('page'),
    'page',
    1
  );

  const pageSize = parsePositiveInteger(
    url.searchParams.get('page_size'),
    'page_size',
    2
  );

  if (pageSize > 50) {
    throw new ApiError(
      400,
      'page_size_too_large',
      'page_size cannot exceed 50.'
    );
  }

  const category = url.searchParams.get('category');
  const author = url.searchParams.get('author');
  const search = url.searchParams.get('q');

  let result = [...books.values()];

  if (category) {
    result = result.filter(
      book => book.category.toLowerCase() === category.toLowerCase()
    );
  }

  if (author) {
    result = result.filter(
      book => book.author.toLowerCase().includes(author.toLowerCase())
    );
  }

  if (search) {
    const needle = search.toLowerCase();

    result = result.filter(
      book =>
        book.title.toLowerCase().includes(needle) ||
        book.author.toLowerCase().includes(needle)
    );
  }

  // Stable ordering is essential for predictable page-based pagination.
  result.sort((a, b) => a.id - b.id);

  return buildPagination(
    result,
    page,
    pageSize,
    `/api/${API_VERSION}/books`
  );
}

function createBook(payload) {
  validateBookPayload(payload);

  const book = {
    id: nextBookId++,
    title: payload.title.trim(),
    author: payload.author.trim(),
    category: payload.category.trim().toLowerCase(),
    publishedYear: payload.publishedYear
  };

  books.set(book.id, book);
  return book;
}

function routeRequest(request, response) {
  const url = new URL(
    request.url,
    `http://${request.headers.host || `${HOST}:${PORT}`}`
  );

  const method = request.method.toUpperCase();
  const path = url.pathname;

  if (method === 'OPTIONS') {
    response.writeHead(204, {
      Allow: 'GET, POST, OPTIONS',
      'Content-Length': '0'
    });
    response.end();
    return;
  }

  if (path === `/api/${API_VERSION}/health` && method === 'GET') {
    sendJson(response, 200, {
      status: 'ok',
      version: API_VERSION,
      timestamp: new Date().toISOString()
    });
    return;
  }

  if (path === `/api/${API_VERSION}/books` && method === 'GET') {
    sendJson(response, 200, listBooks(url));
    return;
  }

  if (path === `/api/${API_VERSION}/books` && method === 'POST') {
    readJsonBody(request)
      .then(payload => {
        const book = createBook(payload);

        sendJson(
          response,
          201,
          {
            data: book,
            links: {
              self: `/api/${API_VERSION}/books/${book.id}`,
              collection: `/api/${API_VERSION}/books`
            }
          },
          {
            Location: `/api/${API_VERSION}/books/${book.id}`
          }
        );
      })
      .catch(error => sendError(response, error));

    return;
  }

  const individualMatch = path.match(
    new RegExp(`^/api/${API_VERSION}/books/(\\d+)$`)
  );

  if (individualMatch && method === 'GET') {
    const id = Number(individualMatch[1]);
    const book = books.get(id);

    if (!book) {
      throw new ApiError(
        404,
        'resource_not_found',
        `Book ${id} does not exist.`
      );
    }

    sendJson(response, 200, {
      data: book,
      links: {
        self: path,
        collection: `/api/${API_VERSION}/books`
      }
    });
    return;
  }

  if (path === '/api/books') {
    throw new ApiError(
      410,
      'deprecated_endpoint',
      `Use /api/${API_VERSION}/books instead.`
    );
  }

  throw new ApiError(
    404,
    'route_not_found',
    'The requested API resource does not exist.'
  );
}

const server = http.createServer((request, response) => {
  try {
    routeRequest(request, response);
  } catch (error) {
    sendError(response, error);
  }
});

function requestJson(method, path, body = undefined) {
  return new Promise((resolve, reject) => {
    const requestBody =
      body === undefined ? undefined : JSON.stringify(body);

    const request = http.request(
      {
        host: HOST,
        port: PORT,
        path,
        method,
        headers: {
          Accept: 'application/json',
          ...(requestBody !== undefined
            ? {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(requestBody)
              }
            : {})
        }
      },
      response => {
        const chunks = [];

        response.on('data', chunk => chunks.push(chunk));

        response.on('end', () => {
          const raw = Buffer.concat(chunks).toString('utf8');

          try {
            resolve({
              status: response.statusCode,
              body: raw ? JSON.parse(raw) : {}
            });
          } catch (error) {
            reject(error);
          }
        });
      }
    );

    request.on('error', reject);

    if (requestBody !== undefined) {
      request.write(requestBody);
    }

    request.end();
  });
}

async function runDemonstration() {
  console.log('REST API URI design');
  console.log('/api/v1/books');
  console.log('/api/v1/books/5');
  console.log('/api/v1/books?page=2&page_size=2');
  console.log('/api/v1/books?category=api-design');
  console.log('/api/v1/books?q=architecture');

  const serverReady = new Promise(resolve => {
    server.once('listening', resolve);
  });

  server.listen(PORT, HOST);
  await serverReady;

  try {
    let result = await requestJson(
      'GET',
      '/api/v1/books?page=1&page_size=2'
    );
    console.log('\nPaginated collection:', result.status);
    console.log(JSON.stringify(result.body, null, 2));

    result = await requestJson(
      'GET',
      '/api/v1/books/3'
    );
    console.log('\nIndividual resource:', result.status);
    console.log(JSON.stringify(result.body, null, 2));

    result = await requestJson(
      'POST',
      '/api/v1/books',
      {
        title: 'RESTful Web APIs',
        author: 'Leonard Richardson',
        category: 'api-design',
        publishedYear: 2013
      }
    );
    console.log('\nCreated resource:', result.status);
    console.log(JSON.stringify(result.body, null, 2));

    result = await requestJson(
      'GET',
      '/api/v1/books/9999'
    );
    console.log('\nMissing resource:', result.status);
    console.log(JSON.stringify(result.body, null, 2));

    result = await requestJson(
      'GET',
      '/api/books'
    );
    console.log('\nDeprecated URI:', result.status);
    console.log(JSON.stringify(result.body, null, 2));
  } finally {
    server.close();
  }
}

runDemonstration().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
