from __future__ import annotations

import json
import logging
import re
import socket
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse


# Backend fundamentals demonstrated here:
# - HTTP server lifecycle
# - request/response construction
# - route matching with parameters
# - middleware composition
# - query-string parsing
# - JSON request/response handling
# - authentication and authorization middleware
# - request logging and timing
# - centralized error handling
# - routing precedence
# - graceful shutdown
# - production-oriented validation and security boundaries


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger("backend-fundamentals")


@dataclass
class Request:
    method: str
    target: str
    path: str
    query: Dict[str, List[str]]
    headers: Dict[str, str]
    body: bytes
    remote_address: str
    route_params: Dict[str, str] = field(default_factory=dict)
    context: Dict[str, object] = field(default_factory=dict)

    @property
    def json(self) -> object:
        if not self.body:
            return None
        content_type = self.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            raise ValueError("Expected application/json content type")
        return json.loads(self.body.decode("utf-8"))


@dataclass
class Response:
    status: int = HTTPStatus.OK
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    @classmethod
    def json(
        cls,
        payload: object,
        status: int = HTTPStatus.OK,
        headers: Optional[Dict[str, str]] = None,
    ) -> "Response":
        response_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
        }
        if headers:
            response_headers.update(headers)

        return cls(
            status=status,
            headers=response_headers,
            body=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        )

    @classmethod
    def text(
        cls,
        value: str,
        status: int = HTTPStatus.OK,
        headers: Optional[Dict[str, str]] = None,
    ) -> "Response":
        response_headers = {
            "Content-Type": "text/plain; charset=utf-8",
        }
        if headers:
            response_headers.update(headers)

        return cls(
            status=status,
            headers=response_headers,
            body=value.encode("utf-8"),
        )


Handler = Callable[[Request], Response]
Middleware = Callable[[Handler], Handler]


class RoutePattern:
    """Compiles /users/{id}/orders/{order_id} into a safe regular expression."""

    PARAMETER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

    def __init__(self, pattern: str):
        if not pattern.startswith("/"):
            raise ValueError("Route pattern must start with /")

        self.pattern = pattern
        self.parameter_names: List[str] = []

        parts = pattern.split("/")
        regex_parts = []

        for part in parts:
            if not part:
                continue

            match = self.PARAMETER.fullmatch(part)
            if match:
                name = match.group(1)
                self.parameter_names.append(name)
                regex_parts.append(r"([^/]+)")
            else:
                regex_parts.append(re.escape(part))

        if pattern == "/":
            expression = r"^/$"
        else:
            expression = "^/" + "/".join(regex_parts) + "/?$"

        self.regex = re.compile(expression)

    def match(self, path: str) -> Optional[Dict[str, str]]:
        match = self.regex.match(path)
        if not match:
            return None

        return {
            name: value
            for name, value in zip(self.parameter_names, match.groups())
        }


@dataclass
class Route:
    method: str
    pattern: RoutePattern
    handler: Handler

    def match(self, method: str, path: str) -> Optional[Dict[str, str]]:
        if self.method != method.upper():
            return None
        return self.pattern.match(path)


class Router:
    """Small framework-style router with explicit route precedence."""

    def __init__(self):
        self.routes: List[Route] = []

    def add(self, method: str, pattern: str, handler: Handler) -> None:
        self.routes.append(
            Route(
                method=method.upper(),
                pattern=RoutePattern(pattern),
                handler=handler,
            )
        )

    def get(self, pattern: str, handler: Handler) -> None:
        self.add("GET", pattern, handler)

    def post(self, pattern: str, handler: Handler) -> None:
        self.add("POST", pattern, handler)

    def put(self, pattern: str, handler: Handler) -> None:
        self.add("PUT", pattern, handler)

    def delete(self, pattern: str, handler: Handler) -> None:
        self.add("DELETE", pattern, handler)

    def dispatch(self, request: Request) -> Response:
        method_exists = False

        # Static routes are checked before parameterized routes.
        # This prevents /health from being accidentally interpreted as
        # /users/{id} in routers where broad patterns overlap.
        ordered_routes = sorted(
            self.routes,
            key=lambda route: sum(
                1 for part in route.pattern.pattern.split("/")
                if part and not RoutePattern.PARAMETER.fullmatch(part)
            ),
            reverse=True,
        )

        for route in ordered_routes:
            params = route.match(request.method, request.path)
            if params is not None:
                request.route_params = params
                return route.handler(request)

            if route.method == request.method.upper():
                method_exists = True

        if method_exists:
            return Response.json(
                {
                    "error": "method_not_allowed",
                    "message": f"Method {request.method} is not allowed for {request.path}",
                },
                status=HTTPStatus.METHOD_NOT_ALLOWED,
                headers={"Allow": self.allowed_methods(request.path)},
            )

        return Response.json(
            {
                "error": "not_found",
                "message": f"No route matches {request.method} {request.path}",
            },
            status=HTTPStatus.NOT_FOUND,
        )

    def allowed_methods(self, path: str) -> str:
        methods = []

        for route in self.routes:
            if route.pattern.match(path) is not None:
                methods.append(route.method)

        return ", ".join(sorted(set(methods)))


def compose(middlewares: Iterable[Middleware], final_handler: Handler) -> Handler:
    handler = final_handler

    for middleware in reversed(list(middlewares)):
        handler = middleware(handler)

    return handler


def request_id_middleware(next_handler: Handler) -> Handler:
    def middleware(request: Request) -> Response:
        request_id = request.headers.get("x-request-id")

        # Client-supplied request IDs are accepted only after length
        # validation. A production system could instead generate IDs
        # unconditionally and merely record the client correlation ID.
        if not request_id or len(request_id) > 80:
            request_id = f"req-{time.time_ns()}"

        request.context["request_id"] = request_id

        response = next_handler(request)
        response.headers["X-Request-ID"] = request_id
        return response

    return middleware


def security_headers_middleware(next_handler: Handler) -> Handler:
    def middleware(request: Request) -> Response:
        response = next_handler(request)

        # These headers are inexpensive baseline defenses for HTTP APIs.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    return middleware


def body_limit_middleware(max_bytes: int) -> Middleware:
    def factory(next_handler: Handler) -> Handler:
        def middleware(request: Request) -> Response:
            if len(request.body) > max_bytes:
                return Response.json(
                    {
                        "error": "payload_too_large",
                        "message": f"Request body exceeds {max_bytes} bytes",
                    },
                    status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                )

            return next_handler(request)

        return middleware

    return factory


def logging_middleware(next_handler: Handler) -> Handler:
    def middleware(request: Request) -> Response:
        started = time.perf_counter()

        try:
            response = next_handler(request)
            return response
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            request_id = request.context.get("request_id", "-")
            logger.info(
                "%s %s -> %s %.2fms request_id=%s",
                request.method,
                request.target,
                request.context.get("response_status", "-"),
                elapsed_ms,
                request_id,
            )

    return middleware


def authentication_middleware(next_handler: Handler) -> Handler:
    def middleware(request: Request) -> Response:
        authorization = request.headers.get("authorization", "")

        # This is intentionally a deterministic demo token rather than a
        # real credential system. Real applications should use signed,
        # rotated credentials and never hard-code production secrets.
        if authorization == "Bearer demo-admin-token":
            request.context["user"] = {
                "id": "u-admin",
                "role": "admin",
            }
        elif authorization == "Bearer demo-user-token":
            request.context["user"] = {
                "id": "u-user",
                "role": "user",
            }
        else:
            return Response.json(
                {
                    "error": "unauthorized",
                    "message": "A valid bearer token is required",
                },
                status=HTTPStatus.UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return next_handler(request)

    return middleware


def require_role(role: str) -> Middleware:
    def factory(next_handler: Handler) -> Handler:
        def middleware(request: Request) -> Response:
            user = request.context.get("user")

            if not isinstance(user, dict) or user.get("role") != role:
                return Response.json(
                    {
                        "error": "forbidden",
                        "message": f"Role '{role}' is required",
                    },
                    status=HTTPStatus.FORBIDDEN,
                )

            return next_handler(request)

        return middleware

    return factory


class UserRepository:
    def __init__(self):
        self.users = {
            "1001": {
                "id": "1001",
                "name": "Asha Sharma",
                "role": "engineer",
            },
            "1002": {
                "id": "1002",
                "name": "Ravi Mehta",
                "role": "reviewer",
            },
        }

    def find(self, user_id: str) -> Optional[dict]:
        return self.users.get(user_id)

    def create(self, name: str, role: str) -> dict:
        if not name.strip():
            raise ValueError("name cannot be empty")

        if role not in {"engineer", "reviewer", "admin"}:
            raise ValueError("unsupported user role")

        next_id = str(max(map(int, self.users.keys())) + 1)

        user = {
            "id": next_id,
            "name": name.strip(),
            "role": role,
        }
        self.users[next_id] = user
        return user


repository = UserRepository()
router = Router()


def health_handler(request: Request) -> Response:
    return Response.json(
        {
            "status": "healthy",
            "service": "backend-fundamentals",
            "server_time": time.time(),
        }
    )


def list_users_handler(request: Request) -> Response:
    role = request.query.get("role", [None])[0]

    users = list(repository.users.values())

    if role:
        users = [user for user in users if user["role"] == role]

    return Response.json(
        {
            "count": len(users),
            "users": users,
        }
    )


def get_user_handler(request: Request) -> Response:
    user_id = request.route_params["user_id"]
    user = repository.find(user_id)

    if user is None:
        return Response.json(
            {
                "error": "user_not_found",
                "user_id": user_id,
            },
            status=HTTPStatus.NOT_FOUND,
        )

    return Response.json(user)


def create_user_handler(request: Request) -> Response:
    try:
        payload = request.json

        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")

        user = repository.create(
            name=str(payload.get("name", "")),
            role=str(payload.get("role", "")),
        )

        return Response.json(
            user,
            status=HTTPStatus.CREATED,
            headers={"Location": f"/users/{user['id']}"},
        )

    except json.JSONDecodeError:
        return Response.json(
            {
                "error": "invalid_json",
                "message": "Request body is not valid JSON",
            },
            status=HTTPStatus.BAD_REQUEST,
        )
    except ValueError as exc:
        return Response.json(
            {
                "error": "validation_error",
                "message": str(exc),
            },
            status=HTTPStatus.BAD_REQUEST,
        )


def delete_user_handler(request: Request) -> Response:
    user_id = request.route_params["user_id"]

    if user_id not in repository.users:
        return Response.json(
            {"error": "user_not_found"},
            status=HTTPStatus.NOT_FOUND,
        )

    del repository.users[user_id]

    return Response.json(
        {
            "deleted": True,
            "user_id": user_id,
        }
    )


router.get("/health", health_handler)
router.get("/users", list_users_handler)
router.get("/users/{user_id}", get_user_handler)

# Creating and deleting users demonstrate route-specific middleware.
create_user_handler_protected = compose(
    [
        authentication_middleware,
        require_role("admin"),
    ],
    create_user_handler,
)

delete_user_handler_protected = compose(
    [
        authentication_middleware,
        require_role("admin"),
    ],
    delete_user_handler,
)

router.post("/users", create_user_handler_protected)
router.delete("/users/{user_id}", delete_user_handler_protected)


def application(request: Request) -> Response:
    try:
        response = router.dispatch(request)
        request.context["response_status"] = response.status
        return response
    except Exception:
        logger.exception("Unhandled application exception")

        response = Response.json(
            {
                "error": "internal_server_error",
                "message": "The server could not complete the request",
                "request_id": request.context.get("request_id"),
            },
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        request.context["response_status"] = response.status
        return response


application_with_middleware = compose(
    [
        request_id_middleware,
        security_headers_middleware,
        body_limit_middleware(1024 * 1024),
        logging_middleware,
    ],
    application,
)


class BackendRequestHandler(BaseHTTPRequestHandler):
    server_version = "BackendFundamentals/1.0"

    def _handle(self) -> None:
        parsed = urlparse(self.path)

        content_length_header = self.headers.get("Content-Length", "0")

        try:
            content_length = int(content_length_header)
        except ValueError:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.end_headers()
            return

        if content_length < 0:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.end_headers()
            return

        body = self.rfile.read(content_length) if content_length else b""

        headers = {
            key.lower(): value.strip()
            for key, value in self.headers.items()
        }

        request = Request(
            method=self.command.upper(),
            target=self.path,
            path=parsed.path,
            query=parse_qs(parsed.query, keep_blank_values=True),
            headers=headers,
            body=body,
            remote_address=self.client_address[0],
        )

        response = application_with_middleware(request)

        self.send_response(response.status)

        response.headers.setdefault(
            "Content-Length",
            str(len(response.body)),
        )

        for name, value in response.headers.items():
            self.send_header(name, value)

        self.end_headers()

        if self.command.upper() != "HEAD":
            self.wfile.write(response.body)

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_DELETE(self) -> None:
        self._handle()

    def do_HEAD(self) -> None:
        self._handle()

    def log_message(self, format: str, *args) -> None:
        # BaseHTTPRequestHandler logs to stderr by default. The application
        # already has structured request logging, so duplicate output is avoided.
        return


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), BackendRequestHandler)

    print(f"Backend server listening at http://{host}:{port}")
    print("GET  /health")
    print("GET  /users")
    print("GET  /users/{id}")
    print("POST /users    Authorization: Bearer demo-admin-token")
    print("DELETE /users/{id}    Authorization: Bearer demo-admin-token")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        # Closing the server releases the listening socket. This matters
        # because an open listening socket can prevent immediate restart.
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    run_server()
