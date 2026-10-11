'use strict';

/*
 * API Fundamentals: REST, Resources, Endpoints, and HTTP
 *
 * This Node.js program focuses on event-driven HTTP behavior. It implements
 * a small REST API with resource routing, JSON representations, validation,
 * HTTP status codes, ETags, conditional GETs, pagination, and an internal
 * client that exercises the endpoints.
 */

const http = require('http');
const crypto = require('crypto');

const HOST = '127.0.0.1';
const PORT = 8081;

class ApiError extends Error {
    constructor(status, message, details = undefined) {
        super(message);
        this.status = status;
        this.details = details;
    }
}

class ResourceRepository {
    constructor() {
        this.resources = new Map();
        this.nextId = 1;
    }

    create(input) {
        this.validate(input);

        const now = new Date().toISOString();
        const resource = {
            id: this.nextId++,
            name: input.name.trim(),
            category: input.category.trim(),
            status: input.status || 'active',
            version: 1,
            createdAt: now,
            updatedAt: now
        };

        this.resources.set(resource.id, resource);
        return resource;
    }

    find(id) {
        const resource = this.resources.get(id);

        if (!resource) {
            throw new ApiError(404, 'Resource not found');
        }

        return resource;
    }

    update(id, input, replace = false) {
        const current = this.find(id);

        const candidate = replace
            ? input
            : {
                name: current.name,
                category: current.category,
                status: current.status,
                ...input
            };

        this.validate(candidate);

        current.name = candidate.name.trim();
        current.category = candidate.category.trim();
        current.status = candidate.status;
        current.version += 1;
        current.updatedAt = new Date().toISOString();

        return current;
    }

    delete(id) {
        if (!this.resources.delete(id)) {
            throw new ApiError(404, 'Resource not found');
        }
    }

    list(category, limit, offset) {
        let result = [...this.resources.values()];

        if (category) {
            result = result.filter(
                item => item.category.toLowerCase() === category.toLowerCase()
            );
        }

        const total = result.length;
        const page = result.slice(offset, offset + limit);

        return {
            data: page,
            pagination: {
                total,
                limit,
                offset,
                returned: page.length
            }
        };
    }

    validate(input) {
        if (!input || typeof input !== 'object' || Array.isArray(input)) {
            throw new ApiError(400, 'JSON body must be an object');
        }

        if (typeof input.name !== 'string' || input.name.trim() === '') {
            throw new ApiError(422, 'name must be a non-empty string');
        }

        if (input.name.trim().length > 100) {
            throw new ApiError(422, 'name cannot exceed 100 characters');
        }

        if (
            typeof input.category !== 'string' ||
            input.category.trim() === ''
        ) {
            throw new ApiError(422, 'category must be a non-empty string');
        }

        const statuses = new Set(['active', 'inactive', 'maintenance']);

        if (!statuses.has(input.status)) {
            throw new ApiError(
                422,
                'status must be active, inactive, or maintenance'
            );
        }
    }
}

function etagFor(resource) {
    const canonical = JSON.stringify({
        id: resource.id,
        version: resource.version,
        updatedAt: resource.updatedAt
    });

    const digest = crypto
        .createHash('sha256')
        .update(canonical)
        .digest('hex')
        .slice(0, 16);

    return `"${digest}"`;
}

function sendJson(response, status, payload, headers = {}) {
    const body = payload === null
        ? ''
        : JSON.stringify(payload);

    response.writeHead(status, {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-store',
        'Content-Length': Buffer.byteLength(body),
        ...headers
    });

    if (body) {
        response.end(body);
    } else {
        response.end();
    }
}

function readJsonBody(request) {
    return new Promise((resolve, reject) => {
        const chunks = [];
        let size = 0;
        const MAX_BODY = 1024 * 1024;

        request.on('data', chunk => {
            size += chunk.length;

            if (size > MAX_BODY) {
                reject(new ApiError(413, 'Request body exceeds 1 MiB'));
                request.destroy();
                return;
            }

            chunks.push(chunk);
        });

        request.on('end', () => {
            if (size === 0) {
                resolve(null);
                return;
            }

            const contentType = request.headers['content-type'] || '';

            if (!contentType.includes('application/json')) {
                reject(
                    new ApiError(
                        415,
                        'JSON requests require application/json'
                    )
                );
                return;
            }

            try {
                resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')));
            } catch {
                reject(new ApiError(400, 'Malformed JSON'));
            }
        });

        request.on('error', reject);
    });
}

async function routeRequest(request, response, repository) {
    try {
        const url = new URL(
            request.url,
            `http://${request.headers.host || `${HOST}:${PORT}`}`
        );

        const method = request.method;
        const pathname = url.pathname;

        if (pathname === '/api/v1/health') {
            if (method !== 'GET') {
                throw new ApiError(405, 'Method not allowed');
            }

            sendJson(response, 200, {
                status: 'ok',
                timestamp: new Date().toISOString()
            });
            return;
        }

        const collectionMatch =
            pathname.match(/^\/api\/v1\/resources\/?$/);

        const memberMatch =
            pathname.match(/^\/api\/v1\/resources\/(\d+)\/?$/);

        if (collectionMatch) {
            await handleCollection(request, response, repository, url);
            return;
        }

        if (memberMatch) {
            await handleMember(
                request,
                response,
                repository,
                Number(memberMatch[1])
            );
            return;
        }

        throw new ApiError(404, 'Endpoint not found');
    } catch (error) {
        if (error instanceof ApiError) {
            sendJson(response, error.status, {
                error: error.message,
                details: error.details
            });
            return;
        }

        console.error(error);
        sendJson(response, 500, {
            error: 'Internal server error'
        });
    }
}

async function handleCollection(request, response, repository, url) {
    if (request.method === 'GET') {
        const rawLimit = Number(url.searchParams.get('limit') || 20);
        const rawOffset = Number(url.searchParams.get('offset') || 0);

        if (
            !Number.isInteger(rawLimit) ||
            !Number.isInteger(rawOffset) ||
            rawLimit < 1 ||
            rawLimit > 100 ||
            rawOffset < 0
        ) {
            throw new ApiError(
                400,
                'limit must be 1-100 and offset must be non-negative integers'
            );
        }

        sendJson(
            response,
            200,
            repository.list(
                url.searchParams.get('category'),
                rawLimit,
                rawOffset
            )
        );
        return;
    }

    if (request.method === 'POST') {
        const body = await readJsonBody(request);
        const resource = repository.create(body);

        sendJson(
            response,
            201,
            resource,
            {
                Location: `/api/v1/resources/${resource.id}`,
                ETag: etagFor(resource)
            }
        );
        return;
    }

    throw new ApiError(405, 'Method not allowed');
}

async function handleMember(request, response, repository, id) {
    const resource = repository.find(id);

    if (request.method === 'GET' || request.method === 'HEAD') {
        const etag = etagFor(resource);

        /*
         * If the representation has not changed, HTTP allows the server to
         * return 304 instead of retransmitting the representation.
         */
        if (request.headers['if-none-match'] === etag) {
            sendJson(response, 304, null, { ETag: etag });
            return;
        }

        if (request.method === 'HEAD') {
            sendJson(response, 200, null, { ETag: etag });
            return;
        }

        sendJson(response, 200, resource, { ETag: etag });
        return;
    }

    if (request.method === 'PUT') {
        const body = await readJsonBody(request);
        const updated = repository.update(id, body, true);

        sendJson(response, 200, updated, {
            ETag: etagFor(updated)
        });
        return;
    }

    if (request.method === 'PATCH') {
        const body = await readJsonBody(request);
        const updated = repository.update(id, body, false);

        sendJson(response, 200, updated, {
            ETag: etagFor(updated)
        });
        return;
    }

    if (request.method === 'DELETE') {
        repository.delete(id);
        sendJson(response, 204, null);
        return;
    }

    throw new ApiError(405, 'Method not allowed');
}

const repository = new ResourceRepository();

repository.create({
    name: 'Order Processing API',
    category: 'application',
    status: 'active'
});

repository.create({
    name: 'Identity Provider',
    category: 'security',
    status: 'active'
});

repository.create({
    name: 'Analytics Warehouse',
    category: 'data',
    status: 'maintenance'
});

const server = http.createServer((request, response) => {
    routeRequest(request, response, repository);
});

function requestJson(method, path, body = undefined, headers = {}) {
    return new Promise((resolve, reject) => {
        const payload = body === undefined
            ? undefined
            : JSON.stringify(body);

        const request = http.request(
            {
                hostname: HOST,
                port: PORT,
                path,
                method,
                headers: {
                    Accept: 'application/json',
                    ...(payload
                        ? {
                            'Content-Type': 'application/json',
                            'Content-Length': Buffer.byteLength(payload)
                        }
                        : {}),
                    ...headers
                }
            },
            response => {
                const chunks = [];

                response.on('data', chunk => chunks.push(chunk));

                response.on('end', () => {
                    const raw = Buffer.concat(chunks).toString('utf8');

                    let parsed = null;
                    if (raw) {
                        try {
                            parsed = JSON.parse(raw);
                        } catch {
                            parsed = raw;
                        }
                    }

                    resolve({
                        status: response.statusCode,
                        headers: response.headers,
                        body: parsed
                    });
                });
            }
        );

        request.on('error', reject);

        if (payload) {
            request.write(payload);
        }

        request.end();
    });
}

async function demonstrateApi() {
    console.log('GET collection');
    console.log(
        await requestJson('GET', '/api/v1/resources?limit=10&offset=0')
    );

    console.log('\nPOST resource');
    const created = await requestJson(
        'POST',
        '/api/v1/resources',
        {
            name: 'Notification Gateway',
            category: 'application',
            status: 'active'
        }
    );
    console.log(created);

    const id = created.body.id;

    console.log('\nGET member');
    const fetched = await requestJson(
        'GET',
        `/api/v1/resources/${id}`
    );
    console.log(fetched);

    console.log('\nConditional GET using ETag');
    console.log(
        await requestJson(
            'GET',
            `/api/v1/resources/${id}`,
            undefined,
            {
                'If-None-Match': fetched.headers.etag
            }
        )
    );

    console.log('\nPATCH member');
    console.log(
        await requestJson(
            'PATCH',
            `/api/v1/resources/${id}`,
            { status: 'maintenance' }
        )
    );

    console.log('\nInvalid endpoint');
    console.log(await requestJson('GET', '/api/v1/unknown'));
}

server.listen(PORT, HOST, async () => {
    console.log(`REST API running at http://${HOST}:${PORT}`);
    try {
        await demonstrateApi();
    } finally {
        server.close();
    }
});
