"use strict";

/*
 * Authentication, sessions, tokens, and authentication flows
 *
 * This file models a browser-oriented authentication service using Node.js
 * standard-library capabilities. It deliberately separates:
 *
 * - credential verification
 * - stateful sessions
 * - short-lived signed access tokens
 * - rotating refresh tokens
 * - authorization
 * - authentication events
 *
 * The JWT implementation is intentionally small so the token mechanics are
 * visible. Production applications should use a maintained security library.
 */

const crypto = require("crypto");
const { EventEmitter } = require("events");

const nowSeconds = () => Math.floor(Date.now() / 1000);

function base64UrlEncode(value) {
    return Buffer.from(value)
        .toString("base64")
        .replace(/\+/g, "-")
        .replace(/\//g, "_")
        .replace(/=+$/g, "");
}

function base64UrlDecode(value) {
    const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
    const padding = "=".repeat((4 - (normalized.length % 4)) % 4);
    return Buffer.from(normalized + padding, "base64");
}

function timingSafeEqualText(a, b) {
    const left = Buffer.from(a);
    const right = Buffer.from(b);

    if (left.length !== right.length) {
        return false;
    }

    return crypto.timingSafeEqual(left, right);
}

function hashPassword(password, salt = crypto.randomBytes(16)) {
    if (typeof password !== "string" || password.length < 12) {
        throw new Error("Password must contain at least 12 characters.");
    }

    const iterations = 310000;
    const digest = crypto.pbkdf2Sync(
        password,
        salt,
        iterations,
        32,
        "sha256"
    );

    return [
        "pbkdf2_sha256",
        iterations,
        base64UrlEncode(salt),
        base64UrlEncode(digest)
    ].join("$");
}

function verifyPassword(password, encoded) {
    try {
        const [algorithm, iterationsText, saltText, digestText] =
            encoded.split("$");

        if (algorithm !== "pbkdf2_sha256") {
            return false;
        }

        const iterations = Number(iterationsText);
        const salt = base64UrlDecode(saltText);
        const expected = base64UrlDecode(digestText);

        const actual = crypto.pbkdf2Sync(
            password,
            salt,
            iterations,
            expected.length,
            "sha256"
        );

        return crypto.timingSafeEqual(actual, expected);
    } catch {
        return false;
    }
}

class TokenService {
    constructor(secret, issuer) {
        if (!Buffer.isBuffer(secret) || secret.length < 32) {
            throw new Error("Signing secret must contain at least 32 bytes.");
        }

        this.secret = secret;
        this.issuer = issuer;
    }

    sign(input) {
        return base64UrlEncode(
            crypto.createHmac("sha256", this.secret)
                .update(input)
                .digest()
        );
    }

    createAccessToken(user, lifetimeSeconds = 600) {
        const header = {
            alg: "HS256",
            typ: "JWT"
        };

        const payload = {
            iss: this.issuer,
            sub: user.id,
            roles: [...user.roles],
            iat: nowSeconds(),
            exp: nowSeconds() + lifetimeSeconds,
            jti: crypto.randomUUID()
        };

        const headerPart = base64UrlEncode(JSON.stringify(header));
        const payloadPart = base64UrlEncode(JSON.stringify(payload));
        const input = `${headerPart}.${payloadPart}`;
        const signature = this.sign(input);

        return `${input}.${signature}`;
    }

    verifyAccessToken(token) {
        const parts = token.split(".");

        if (parts.length !== 3) {
            throw new Error("Malformed access token.");
        }

        const [headerPart, payloadPart, suppliedSignature] = parts;
        const expectedSignature = this.sign(
            `${headerPart}.${payloadPart}`
        );

        if (!timingSafeEqualText(suppliedSignature, expectedSignature)) {
            throw new Error("Invalid access-token signature.");
        }

        let header;
        let payload;

        try {
            header = JSON.parse(base64UrlDecode(headerPart).toString("utf8"));
            payload = JSON.parse(base64UrlDecode(payloadPart).toString("utf8"));
        } catch {
            throw new Error("Invalid token encoding.");
        }

        if (header.alg !== "HS256") {
            throw new Error("Unexpected token algorithm.");
        }

        if (payload.iss !== this.issuer) {
            throw new Error("Unexpected token issuer.");
        }

        if (
            typeof payload.exp !== "number" ||
            nowSeconds() >= payload.exp
        ) {
            throw new Error("Access token has expired.");
        }

        if (typeof payload.sub !== "string") {
            throw new Error("Token subject is missing.");
        }

        return payload;
    }
}

class SessionManager {
    constructor() {
        this.sessions = new Map();
    }

    create(userId, metadata = {}) {
        const sessionId = crypto.randomBytes(32).toString("base64url");
        const csrfToken = crypto.randomBytes(32).toString("base64url");
        const createdAt = Date.now();

        const session = {
            id: sessionId,
            userId,
            csrfToken,
            createdAt,
            expiresAt: createdAt + 8 * 60 * 60 * 1000,
            lastSeenAt: createdAt,
            revoked: false,
            ipAddress: metadata.ipAddress ?? null,
            userAgent: metadata.userAgent ?? null
        };

        this.sessions.set(sessionId, session);
        return session;
    }

    getValid(sessionId) {
        const session = this.sessions.get(sessionId);

        if (!session) {
            throw new Error("Session does not exist.");
        }

        if (session.revoked) {
            throw new Error("Session has been revoked.");
        }

        if (Date.now() >= session.expiresAt) {
            session.revoked = true;
            throw new Error("Session has expired.");
        }

        session.lastSeenAt = Date.now();
        return session;
    }

    revoke(sessionId) {
        const session = this.sessions.get(sessionId);

        if (session) {
            session.revoked = true;
        }
    }

    revokeAllForUser(userId) {
        let count = 0;

        for (const session of this.sessions.values()) {
            if (session.userId === userId && !session.revoked) {
                session.revoked = true;
                count += 1;
            }
        }

        return count;
    }
}

class RefreshTokenManager {
    constructor() {
        this.tokens = new Map();
    }

    hash(token) {
        return crypto
            .createHash("sha256")
            .update(token)
            .digest("hex");
    }

    issue(userId, lifetimeMilliseconds = 30 * 24 * 60 * 60 * 1000) {
        const token = crypto.randomBytes(48).toString("base64url");
        const tokenHash = this.hash(token);

        this.tokens.set(tokenHash, {
            tokenHash,
            userId,
            expiresAt: Date.now() + lifetimeMilliseconds,
            revoked: false,
            replacedBy: null
        });

        return token;
    }

    rotate(token) {
        const tokenHash = this.hash(token);
        const record = this.tokens.get(tokenHash);

        if (!record) {
            throw new Error("Unknown refresh token.");
        }

        if (record.revoked) {
            throw new Error("Refresh token has already been used or revoked.");
        }

        if (Date.now() >= record.expiresAt) {
            record.revoked = true;
            throw new Error("Refresh token has expired.");
        }

        record.revoked = true;

        const replacement = this.issue(record.userId);
        record.replacedBy = this.hash(replacement);

        return replacement;
    }

    revoke(token) {
        const record = this.tokens.get(this.hash(token));

        if (record) {
            record.revoked = true;
        }
    }
}

class LoginThrottle {
    constructor(maxAttempts = 5, windowMilliseconds = 5 * 60 * 1000) {
        this.maxAttempts = maxAttempts;
        this.windowMilliseconds = windowMilliseconds;
        this.attempts = new Map();
    }

    allowed(key) {
        const currentTime = Date.now();
        const cutoff = currentTime - this.windowMilliseconds;
        const existing = this.attempts.get(key) ?? [];

        const recent = existing.filter(
            timestamp => timestamp >= cutoff
        );

        if (recent.length >= this.maxAttempts) {
            this.attempts.set(key, recent);
            return false;
        }

        recent.push(currentTime);
        this.attempts.set(key, recent);
        return true;
    }

    clear(key) {
        this.attempts.delete(key);
    }
}

class AuthenticationService extends EventEmitter {
    constructor() {
        super();

        this.users = new Map();
        this.sessions = new SessionManager();
        this.refreshTokens = new RefreshTokenManager();
        this.throttle = new LoginThrottle();
        this.tokens = new TokenService(
            crypto.randomBytes(32),
            "authentication-demo"
        );
    }

    register(username, password, roles = ["user"]) {
        const normalized = username.trim().toLowerCase();

        if (!normalized.includes("@")) {
            throw new Error("Username must be a valid email-like identifier.");
        }

        if (this.users.has(normalized)) {
            throw new Error("User already exists.");
        }

        const user = {
            id: crypto.randomUUID(),
            username: normalized,
            passwordHash: hashPassword(password),
            roles: new Set(roles),
            active: true
        };

        this.users.set(normalized, user);

        this.emit("user.registered", {
            userId: user.id,
            username: user.username
        });

        return user;
    }

    login(username, password, metadata = {}) {
        const normalized = username.trim().toLowerCase();
        const key = `${normalized}:${metadata.ipAddress ?? "unknown"}`;

        if (!this.throttle.allowed(key)) {
            throw new Error("Authentication temporarily rate-limited.");
        }

        const user = this.users.get(normalized);

        if (
            !user ||
            !user.active ||
            !verifyPassword(password, user.passwordHash)
        ) {
            this.emit("authentication.failed", {
                username: normalized,
                ipAddress: metadata.ipAddress ?? null
            });

            throw new Error("Invalid credentials.");
        }

        this.throttle.clear(key);

        /*
         * A fresh session identifier is created after successful authentication.
         * Reusing an identifier supplied before login could enable session fixation.
         */
        const session = this.sessions.create(user.id, metadata);
        const accessToken = this.tokens.createAccessToken(user);
        const refreshToken = this.refreshTokens.issue(user.id);

        this.emit("authentication.succeeded", {
            userId: user.id,
            sessionId: session.id
        });

        return {
            session,
            accessToken,
            refreshToken
        };
    }

    authenticateSession(sessionId) {
        const session = this.sessions.getValid(sessionId);
        const user = [...this.users.values()].find(
            candidate => candidate.id === session.userId
        );

        if (!user || !user.active) {
            throw new Error("Session owner is inactive.");
        }

        return user;
    }

    authenticateAccessToken(token) {
        const claims = this.tokens.verifyAccessToken(token);
        const user = [...this.users.values()].find(
            candidate => candidate.id === claims.sub
        );

        if (!user || !user.active) {
            throw new Error("Token subject is inactive.");
        }

        return user;
    }

    refresh(refreshToken) {
        const replacement = this.refreshTokens.rotate(refreshToken);
        const replacementHash = this.refreshTokens.hash(replacement);
        const record = this.refreshTokens.tokens.get(replacementHash);

        if (!record) {
            throw new Error("Refresh-token rotation failed.");
        }

        const user = [...this.users.values()].find(
            candidate => candidate.id === record.userId
        );

        if (!user || !user.active) {
            throw new Error("Refresh token belongs to inactive user.");
        }

        return {
            accessToken: this.tokens.createAccessToken(user),
            refreshToken: replacement
        };
    }

    logout(sessionId, refreshToken) {
        this.sessions.revoke(sessionId);
        this.refreshTokens.revoke(refreshToken);

        this.emit("authentication.logout", { sessionId });
    }
}

function authorize(user, requiredRole) {
    if (!user.roles.has(requiredRole)) {
        throw new Error(
            `Authorization denied: role '${requiredRole}' is required.`
        );
    }
}

function createSecurityCookie(name, value, maxAgeSeconds) {
    /*
     * HttpOnly prevents browser JavaScript from reading the cookie.
     * Secure requires HTTPS. SameSite limits cross-site cookie transmission.
     */
    return [
        `${name}=${value}`,
        "Path=/",
        "HttpOnly",
        "Secure",
        "SameSite=Lax",
        `Max-Age=${maxAgeSeconds}`
    ].join("; ");
}

async function demonstrateAsyncAuthentication(service, user) {
    /*
     * Authentication systems are often embedded in event-driven HTTP servers.
     * A Promise here demonstrates how token validation can participate in an
     * asynchronous request pipeline without blocking the event loop.
     */
    return Promise.resolve().then(() => {
        const login = service.login(
            user.username,
            "Correct-Horse-Battery-9!",
            {
                ipAddress: "203.0.113.50",
                userAgent: "Browser/1.0"
            }
        );

        const authenticated = service.authenticateAccessToken(
            login.accessToken
        );

        authorize(authenticated, "reviewer");

        return login;
    });
}

async function main() {
    const service = new AuthenticationService();

    service.on("authentication.failed", event => {
        console.log(
            `Authentication failure for ${event.username} from ${event.ipAddress}`
        );
    });

    service.on("authentication.succeeded", event => {
        console.log(`Authentication succeeded for user ${event.userId}`);
    });

    service.on("authentication.logout", event => {
        console.log(`Session logged out: ${event.sessionId.slice(0, 12)}...`);
    });

    const user = service.register(
        "alice@example.com",
        "Correct-Horse-Battery-9!",
        ["user", "reviewer"]
    );

    console.log("Registered:", user.username);
    console.log(
        "Password verification:",
        verifyPassword("Correct-Horse-Battery-9!", user.passwordHash)
    );

    const login = await demonstrateAsyncAuthentication(service, user);

    console.log(
        "Session authenticated:",
        service.authenticateSession(login.session.id).username
    );

    console.log(
        "Access token:",
        `${login.accessToken.slice(0, 35)}...`
    );

    const cookie = createSecurityCookie(
        "session_id",
        login.session.id,
        8 * 60 * 60
    );

    console.log("Secure session cookie:");
    console.log(cookie);

    const refreshed = service.refresh(login.refreshToken);

    console.log(
        "Rotated refresh token:",
        `${refreshed.refreshToken.slice(0, 20)}...`
    );

    try {
        service.refresh(login.refreshToken);
    } catch (error) {
        console.log("Refresh-token replay blocked:", error.message);
    }

    try {
        authorize(user, "admin");
    } catch (error) {
        console.log(error.message);
    }

    service.logout(login.session.id, refreshed.refreshToken);

    try {
        service.authenticateSession(login.session.id);
    } catch (error) {
        console.log("Logged-out session rejected:", error.message);
    }

    console.log("\nAuthentication flow completed.");
}

main().catch(error => {
    console.error("Fatal authentication demonstration error:", error.message);
    process.exitCode = 1;
});
