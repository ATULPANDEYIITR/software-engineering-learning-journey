#!/usr/bin/env python3
"""
HTTP Deep Dive: Methods, Status Codes, Headers, and Cookies

A self-contained learning and simulation program covering:
- HTTP request methods and their semantics
- Status-code classes and practical interpretation
- Request and response headers
- Cookie creation, parsing, expiration, security attributes, and sessions
- Conditional requests and caching headers
- Content negotiation
- Redirects
- Authentication-related headers
- CORS-related headers
- Retry and rate-limit headers
- A small HTTP server that demonstrates the concepts without external packages
"""

from __future__ import annotations

import http.server
import json
import secrets
import socketserver
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import formatdate, parsedate_to_datetime
from http import HTTPStatus
from http.cookies import SimpleCookie
from typing import Dict, Iterable, Optional
from urllib.parse import parse_qs, urlencode, urlparse


# ---------------------------------------------------------------------------
# HTTP methods
# ---------------------------------------------------------------------------

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE", "TRACE"}
METHOD_PURPOSES = {
    "GET": "Retrieve a representation of a resource.",
    "HEAD": "Retrieve response metadata without a response body.",
    "POST": "Submit data for resource-specific processing.",
    "PUT": "Create or completely replace the target representation.",
    "PATCH": "Partially modify a resource.",
    "DELETE": "Remove the target resource.",
    "OPTIONS": "Discover communication options supported by a target.",
    "TRACE": "Diagnostic loop-back request; normally disabled in production.",
    "CONNECT": "Establish a tunnel, commonly through an HTTP proxy.",
}


def explain_method(method: str) -> None:
    method = method.upper()
    if method not in METHOD_PURPOSES:
        print(f"Unknown method: {method}")
        return

    print(f"\nHTTP method: {method}")
    print(f"Purpose: {METHOD_PURPOSES[method]}")
    print(f"Safe: {'yes' if method in SAFE_METHODS else 'no'}")
    print(f"Idempotent: {'yes' if method in IDEMPOTENT_METHODS else 'no'}")

    if method == "POST":
        print("Repeated POST requests may create multiple effects.")
    elif method == "PUT":
        print("PUT is normally used when the client knows the target resource URI.")
    elif method == "PATCH":
        print("PATCH communicates a partial modification rather than full replacement.")
    elif method == "DELETE":
        print("A repeated DELETE should converge on the resource being absent.")
    elif method == "HEAD":
        print("The server sends the same relevant metadata as GET but omits the body.")


# ---------------------------------------------------------------------------
# Status codes
# ---------------------------------------------------------------------------

def classify_status(code: int) -> str:
    if 100 <= code <= 199:
        return "Informational"
    if 200 <= code <= 299:
        return "Successful"
    if 300 <= code <= 399:
        return "Redirection"
    if 400 <= code <= 499:
        return "Client error"
    if 500 <= code <= 599:
        return "Server error"
    return "Invalid HTTP status code"


def explain_status(code: int) -> None:
    try:
        status = HTTPStatus(code)
    except ValueError:
        print(f"{code}: unknown status")
        return

    print(f"{code} {status.phrase}")
    print(f"Class: {classify_status(code)}")

    explanations = {
        200: "The request succeeded.",
        201: "A resource was created. Location may identify the new resource.",
        204: "The operation succeeded without a response body.",
        206: "The server returned a requested byte range.",
        301: "The resource has a permanent redirect target.",
        302: "The resource is temporarily redirected.",
        304: "The cached representation remains valid; the client can reuse it.",
        307: "Temporary redirect while preserving the request method.",
        308: "Permanent redirect while preserving the request method.",
        400: "The server cannot process the request syntax or data.",
        401: "Authentication credentials are required or invalid.",
        403: "The server understood the request but refuses to authorize it.",
        404: "The requested resource is not available.",
        405: "The method is not supported for the target resource.",
        409: "The request conflicts with the current resource state.",
        412: "A conditional request failed its precondition.",
        415: "The submitted representation format is unsupported.",
        422: "The syntax is valid but the semantic content cannot be processed.",
        429: "The client has exceeded a rate limit.",
        500: "The server encountered an unexpected condition.",
        502: "A gateway or proxy received an invalid upstream response.",
        503: "The service is temporarily unavailable.",
        504: "A gateway or proxy timed out waiting for an upstream service.",
    }

    if code in explanations:
        print(explanations[code])


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------

@dataclass
class HTTPHeaders:
    """
    A small case-insensitive header collection.

    HTTP field names are case-insensitive. The original spelling is retained
    for display while lookup uses lowercase names.
    """

    _values: Dict[str, tuple[str, str]] = field(default_factory=dict)

    def set(self, name: str, value: str) -> None:
        self._values[name.lower()] = (name, value)

    def add(self, name: str, value: str) -> None:
        key = name.lower()
        if key in self._values:
            original, old_value = self._values[key]
            self._values[key] = (original, f"{old_value}, {value}")
        else:
            self._values[key] = (name, value)

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        item = self._values.get(name.lower())
        return default if item is None else item[1]

    def remove(self, name: str) -> None:
        self._values.pop(name.lower(), None)

    def items(self) -> Iterable[tuple[str, str]]:
        return ((original, value) for original, value in self._values.values())

    def __contains__(self, name: str) -> bool:
        return name.lower() in self._values

    def __str__(self) -> str:
        return "\n".join(f"{name}: {value}" for name, value in self.items())


def demonstrate_headers() -> None:
    headers = HTTPHeaders()

    headers.set("Host", "api.example.test")
    headers.set("Accept", "application/json")
    headers.set("Content-Type", "application/json")
    headers.set("Content-Length", "27")
    headers.set("Authorization", "Bearer example-token")
    headers.set("User-Agent", "HTTPDeepDive/1.0")
    headers.set("Cache-Control", "no-cache")
    headers.set("If-None-Match", '"profile-v7"')

    print("\nRequest headers:")
    print(headers)

    print("\nCase-insensitive lookup:")
    print(f"accept -> {headers.get('accept')}")
    print(f"ACCEPT -> {headers.get('ACCEPT')}")

    response = HTTPHeaders()
    response.set("Content-Type", "application/json; charset=utf-8")
    response.set("Cache-Control", "private, max-age=60")
    response.set("ETag", '"profile-v7"')
    response.set("Vary", "Accept-Encoding")
    response.set("X-Request-ID", secrets.token_hex(8))

    print("\nResponse headers:")
    print(response)


# ---------------------------------------------------------------------------
# Cookie handling
# ---------------------------------------------------------------------------

@dataclass
class CookiePolicy:
    name: str
    secure: bool = True
    http_only: bool = True
    same_site: str = "Lax"
    path: str = "/"
    max_age: Optional[int] = None
    domain: Optional[str] = None

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Cookie name cannot be empty.")

        if self.same_site not in {"Strict", "Lax", "None"}:
            raise ValueError("SameSite must be Strict, Lax, or None.")

        if self.same_site == "None" and not self.secure:
            raise ValueError("SameSite=None requires Secure in modern browsers.")

        if self.max_age is not None and self.max_age < 0:
            raise ValueError("Max-Age cannot be negative for this policy object.")


def create_cookie_header(
    name: str,
    value: str,
    *,
    secure: bool = True,
    http_only: bool = True,
    same_site: str = "Lax",
    path: str = "/",
    max_age: Optional[int] = None,
) -> str:
    policy = CookiePolicy(
        name=name,
        secure=secure,
        http_only=http_only,
        same_site=same_site,
        path=path,
        max_age=max_age,
    )
    policy.validate()

    cookie = SimpleCookie()
    cookie[name] = value
    morsel = cookie[name]
    morsel["path"] = path
    morsel["samesite"] = same_site

    if secure:
        morsel["secure"] = True

    if http_only:
        morsel["httponly"] = True

    if max_age is not None:
        morsel["max-age"] = str(max_age)

    return morsel.OutputString()


def delete_cookie_header(name: str, path: str = "/") -> str:
    cookie = SimpleCookie()
    cookie[name] = ""
    cookie[name]["path"] = path
    cookie[name]["max-age"] = "0"
    cookie[name]["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
    cookie[name]["httponly"] = True
    cookie[name]["secure"] = True
    cookie[name]["samesite"] = "Lax"
    return cookie[name].OutputString()


def parse_cookie_header(header: str) -> Dict[str, str]:
    cookie = SimpleCookie()
    cookie.load(header)
    return {key: morsel.value for key, morsel in cookie.items()}


def demonstrate_cookies() -> None:
    print("\nSession cookie:")
    session_header = create_cookie_header(
        "session_id",
        secrets.token_urlsafe(24),
        secure=True,
        http_only=True,
        same_site="Lax",
        path="/",
        max_age=3600,
    )
    print(session_header)

    print("\nParsed Cookie request header:")
    request_cookie = "session_id=abc123; theme=dark; locale=en-IN"
    print(parse_cookie_header(request_cookie))

    print("\nCookie deletion:")
    print(delete_cookie_header("session_id"))

    print("\nCookie security considerations:")
    print("- Secure limits transmission to HTTPS.")
    print("- HttpOnly prevents normal JavaScript access through document.cookie.")
    print("- SameSite controls cross-site cookie sending behavior.")
    print("- Path limits the URL paths to which the cookie is sent.")
    print("- Session identifiers should be unpredictable and server-side state should")
    print("  be protected from fixation and unauthorized reuse.")


# ---------------------------------------------------------------------------
# Conditional requests and caching
# ---------------------------------------------------------------------------

def conditional_get(etag: str, if_none_match: Optional[str]) -> tuple[int, str]:
    if if_none_match is not None and if_none_match.strip() == etag:
        return 304, "Not Modified"
    return 200, "Fresh representation required"


def demonstrate_caching() -> None:
    etag = '"article-42-v9"'

    print("\nConditional request:")
    status, message = conditional_get(etag, '"article-42-v9"')
    print(status, message)

    status, message = conditional_get(etag, '"article-42-v8"')
    print(status, message)

    last_modified = formatdate(time.time() - 3600, usegmt=True)
    print(f"\nLast-Modified: {last_modified}")
    print("ETag is normally stronger and more precise for representation identity.")
    print("Cache-Control defines caching behavior; ETag and Last-Modified support validation.")


# ---------------------------------------------------------------------------
# Content negotiation
# ---------------------------------------------------------------------------

def negotiate_content_type(accept_header: str) -> str:
    """
    Small demonstration of server-side content negotiation.

    This intentionally handles common media-type choices rather than attempting
    to implement every detail of RFC-quality Accept parsing.
    """
    accepted = [
        item.strip().lower()
        for item in accept_header.split(",")
        if item.strip()
    ]

    for media_type in accepted:
        if media_type in {"application/json", "*/*"}:
            return "application/json"

    for media_type in accepted:
        if media_type == "text/plain":
            return "text/plain"

    return "406 Not Acceptable"


def demonstrate_content_negotiation() -> None:
    print("\nContent negotiation:")
    for accept in (
        "application/json, text/plain;q=0.8",
        "text/plain",
        "application/xml",
    ):
        print(f"Accept: {accept}")
        print(f"Selected representation: {negotiate_content_type(accept)}")


# ---------------------------------------------------------------------------
# HTTP request model
# ---------------------------------------------------------------------------

@dataclass
class HTTPRequest:
    method: str
    target: str
    headers: HTTPHeaders
    body: bytes = b""

    def validate(self) -> None:
        self.method = self.method.upper()

        if self.method not in METHOD_PURPOSES:
            raise ValueError(f"Unsupported demonstration method: {self.method}")

        parsed = urlparse(self.target)
        if not parsed.path:
            raise ValueError("HTTP request target must contain a path.")

        declared_length = self.headers.get("Content-Length")
        if declared_length is not None:
            try:
                expected = int(declared_length)
            except ValueError as exc:
                raise ValueError("Content-Length must be an integer.") from exc

            if expected != len(self.body):
                raise ValueError(
                    f"Content-Length={expected} does not match "
                    f"actual body length={len(self.body)}."
                )


def demonstrate_request_validation() -> None:
    request = HTTPRequest(
        method="POST",
        target="/api/orders",
        headers=HTTPHeaders(),
        body=b'{"item":"keyboard"}',
    )
    request.headers.set("Content-Type", "application/json")
    request.headers.set("Content-Length", str(len(request.body)))
    request.validate()

    print("\nValidated request:")
    print(f"{request.method} {request.target}")
    print(f"Body: {request.body.decode('utf-8')}")


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

@dataclass
class RateLimiter:
    limit: int
    window_seconds: int
    requests: Dict[str, list[float]] = field(default_factory=dict)

    def allow(self, client_id: str) -> tuple[bool, int]:
        now = time.time()
        history = self.requests.setdefault(client_id, [])

        cutoff = now - self.window_seconds
        history[:] = [timestamp for timestamp in history if timestamp > cutoff]

        if len(history) >= self.limit:
            retry_after = max(
                1,
                int(self.window_seconds - (now - history[0])),
            )
            return False, retry_after

        history.append(now)
        return True, 0


def demonstrate_rate_limiting() -> None:
    limiter = RateLimiter(limit=3, window_seconds=5)

    print("\nRate limiting:")
    for attempt in range(5):
        allowed, retry_after = limiter.allow("client-42")
        if allowed:
            print(f"Request {attempt + 1}: 200 OK")
        else:
            print(
                f"Request {attempt + 1}: 429 Too Many Requests; "
                f"Retry-After: {retry_after}"
            )


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class DeepDiveHandler(http.server.BaseHTTPRequestHandler):
    server_version = "HTTPDeepDive/1.0"

    # Shared state intentionally kept small for this educational server.
    sessions: Dict[str, dict] = {}
    resource_etag = '"resource-v3"'

    def send_json(
        self,
        status: int,
        payload: object,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")

        if extra_headers:
            for name, value in extra_headers.items():
                self.send_header(name, value)

        self.end_headers()

        if self.command != "HEAD":
            self.wfile.write(body)

    def read_json_body(self) -> object:
        length_header = self.headers.get("Content-Length")

        if length_header is None:
            raise ValueError("Content-Length is required for this demonstration.")

        try:
            length = int(length_header)
        except ValueError as exc:
            raise ValueError("Content-Length must be numeric.") from exc

        if length < 0 or length > 1_000_000:
            raise ValueError("Request body size is outside the allowed range.")

        raw = self.rfile.read(length)

        if len(raw) != length:
            raise ValueError("Incomplete request body.")

        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Body must contain valid UTF-8 JSON.") from exc

    def authenticate(self) -> Optional[dict]:
        cookie_header = self.headers.get("Cookie", "")
        cookies = parse_cookie_header(cookie_header)
        session_id = cookies.get("session_id")

        if not session_id:
            return None

        return self.sessions.get(session_id)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_json(
                200,
                {
                    "service": "HTTP Deep Dive Demo",
                    "methods": [
                        "GET",
                        "HEAD",
                        "POST",
                        "PUT",
                        "PATCH",
                        "DELETE",
                        "OPTIONS",
                    ],
                    "endpoints": {
                        "/": "API description",
                        "/resource": "Conditional GET demonstration",
                        "/login": "Creates a demonstration session",
                        "/me": "Reads the session cookie",
                        "/redirect": "Demonstrates redirection",
                    },
                },
            )
            return

        if parsed.path == "/resource":
            if_none_match = self.headers.get("If-None-Match")

            if if_none_match == self.resource_etag:
                self.send_response(304)
                self.send_header("ETag", self.resource_etag)
                self.send_header("Cache-Control", "private, max-age=60")
                self.end_headers()
                return

            self.send_json(
                200,
                {
                    "id": 42,
                    "name": "HTTP protocol resource",
                    "version": 3,
                },
                {
                    "ETag": self.resource_etag,
                    "Cache-Control": "private, max-age=60",
                    "Vary": "Accept-Encoding",
                },
            )
            return

        if parsed.path == "/login":
            session_id = secrets.token_urlsafe(32)
            self.sessions[session_id] = {
                "user": "developer@example.test",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            cookie = create_cookie_header(
                "session_id",
                session_id,
                secure=False,
                http_only=True,
                same_site="Lax",
                path="/",
                max_age=3600,
            )

            self.send_json(
                200,
                {"authenticated": True, "user": "developer@example.test"},
                {"Set-Cookie": cookie},
            )
            return

        if parsed.path == "/me":
            session = self.authenticate()

            if session is None:
                self.send_json(
                    401,
                    {"error": "authentication_required"},
                    {"WWW-Authenticate": 'Bearer realm="demo"'},
                )
                return

            self.send_json(200, session)
            return

        if parsed.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_json(404, {"error": "resource_not_found"})

    def do_HEAD(self) -> None:
        # Reuse GET semantics while suppressing the body in send_json.
        self.do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path != "/resource":
            self.send_json(404, {"error": "resource_not_found"})
            return

        content_type = self.headers.get("Content-Type", "")

        if not content_type.startswith("application/json"):
            self.send_json(
                415,
                {"error": "unsupported_media_type"},
            )
            return

        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return

        if not isinstance(payload, dict):
            self.send_json(422, {"error": "JSON object required"})
            return

        if not payload.get("name"):
            self.send_json(
                422,
                {"error": "name is required"},
            )
            return

        location = "/resource/43"

        self.send_json(
            201,
            {
                "created": True,
                "resource": payload,
            },
            {"Location": location},
        )

    def do_PUT(self) -> None:
        if urlparse(self.path).path != "/resource":
            self.send_json(404, {"error": "resource_not_found"})
            return

        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return

        if not isinstance(payload, dict):
            self.send_json(422, {"error": "JSON object required"})
            return

        self.send_json(
            200,
            {
                "replaced": True,
                "resource": payload,
            },
        )

    def do_PATCH(self) -> None:
        if urlparse(self.path).path != "/resource":
            self.send_json(404, {"error": "resource_not_found"})
            return

        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return

        if not isinstance(payload, dict):
            self.send_json(422, {"error": "JSON object required"})
            return

        self.send_json(
            200,
            {
                "patched_fields": list(payload.keys()),
                "changes": payload,
            },
        )

    def do_DELETE(self) -> None:
        if urlparse(self.path).path != "/resource":
            self.send_json(404, {"error": "resource_not_found"})
            return

        self.send_response(204)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_OPTIONS(self) -> None:
        if urlparse(self.path).path != "/resource":
            self.send_json(404, {"error": "resource_not_found"})
            return

        self.send_response(204)
        self.send_header(
            "Allow",
            "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS",
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization",
        )
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def log_message(self, format_string: str, *args: object) -> None:
        # Keep the demonstration server readable while retaining request logs.
        print(f"[HTTP] {self.address_string()} - {format_string % args}")


def start_demo_server() -> tuple[socketserver.TCPServer, threading.Thread]:
    server = socketserver.ThreadingTCPServer(
        ("127.0.0.1", 8080),
        DeepDiveHandler,
    )
    server.daemon_threads = True

    thread = threading.Thread(
        target=server.serve_forever,
        name="http-demo-server",
        daemon=True,
    )
    thread.start()

    return server, thread


# ---------------------------------------------------------------------------
# URL and header utility demonstrations
# ---------------------------------------------------------------------------

def demonstrate_url_query_parameters() -> None:
    query = {
        "status": "active",
        "limit": "25",
        "tag": ["http", "web"],
    }

    encoded = urlencode(query, doseq=True)
    url = f"https://api.example.test/resources?{encoded}"

    parsed = urlparse(url)
    parameters = parse_qs(parsed.query)

    print("\nURL query parameters:")
    print(f"URL: {url}")
    print(f"Path: {parsed.path}")
    print(f"Parsed query: {parameters}")


def demonstrate_http_dates() -> None:
    current = formatdate(time.time(), usegmt=True)
    parsed = parsedate_to_datetime(current)

    print("\nHTTP date:")
    print(f"Generated: {current}")
    print(f"Parsed UTC timestamp: {parsed.isoformat()}")


def demonstrate_authentication_headers() -> None:
    headers = HTTPHeaders()

    headers.set(
        "WWW-Authenticate",
        'Basic realm="admin", charset="UTF-8"',
    )

    print("\nAuthentication challenge:")
    print(headers)

    print(
        "A 401 response indicates that authentication is required; "
        "WWW-Authenticate describes an authentication challenge."
    )
    print(
        "A 403 response is different: the server understood the request "
        "but refuses authorization."
    )


# ---------------------------------------------------------------------------
# End-to-end demonstration
# ---------------------------------------------------------------------------

def run_learning_demo() -> None:
    print("=" * 72)
    print("HTTP DEEP DIVE")
    print("Methods, Status Codes, Headers, and Cookies")
    print("=" * 72)

    print("\n--- Methods ---")
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
        explain_method(method)

    print("\n--- Status codes ---")
    for code in (200, 201, 204, 301, 304, 307, 400, 401, 403, 404, 409, 412, 415, 422, 429, 500, 502, 503):
        explain_status(code)

    print("\n--- Headers ---")
    demonstrate_headers()

    print("\n--- Cookies ---")
    demonstrate_cookies()

    print("\n--- Conditional requests and caching ---")
    demonstrate_caching()

    print("\n--- Content negotiation ---")
    demonstrate_content_negotiation()

    print("\n--- Request validation ---")
    demonstrate_request_validation()

    print("\n--- Rate limiting ---")
    demonstrate_rate_limiting()

    print("\n--- URL parsing and query parameters ---")
    demonstrate_url_query_parameters()

    print("\n--- HTTP dates ---")
    demonstrate_http_dates()

    print("\n--- Authentication headers ---")
    demonstrate_authentication_headers()


def main() -> None:
    run_learning_demo()

    print("\n--- Local HTTP server ---")
    try:
        server, _ = start_demo_server()
    except OSError as exc:
        print(f"Could not start server on 127.0.0.1:8080: {exc}")
        return

    print("Server started at http://127.0.0.1:8080")
    print("Use a browser or HTTP client to exercise the endpoints.")
    print("Press Ctrl+C to stop the server.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
