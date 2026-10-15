from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """
    PBKDF2 is available in Python's standard library and is suitable for
    demonstrating password hashing without storing the original password.
    Production systems should choose work factors appropriate to their threat model.
    """
    if not password:
        raise ValueError("Password cannot be empty.")

    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        310_000,
    )
    return f"pbkdf2_sha256$310000${b64url_encode(salt)}${b64url_encode(derived)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)
        salt = b64url_decode(salt_text)
        expected = b64url_decode(digest_text)

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    roles: set[str] = field(default_factory=lambda: {"user"})
    active: bool = True


@dataclass
class Session:
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime
    csrf_token: str
    revoked: bool = False
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def is_valid(self, now: Optional[datetime] = None) -> bool:
        now = now or utc_now()
        return not self.revoked and now < self.expires_at


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(
        self,
        user_id: str,
        lifetime: timedelta,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Session:
        now = utc_now()
        session = Session(
            session_id=secrets.token_urlsafe(32),
            user_id=user_id,
            created_at=now,
            expires_at=now + lifetime,
            last_seen_at=now,
            csrf_token=secrets.token_urlsafe(32),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session is None or not session.is_valid():
            return None
        return session

    def touch(self, session_id: str) -> Session:
        session = self.get(session_id)
        if session is None:
            raise AuthenticationError("Session is invalid or expired.")
        session.last_seen_at = utc_now()
        return session

    def revoke(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.revoked = True
        return True

    def revoke_user_sessions(self, user_id: str) -> int:
        count = 0
        for session in self._sessions.values():
            if session.user_id == user_id and not session.revoked:
                session.revoked = True
                count += 1
        return count

    def purge_expired(self) -> int:
        expired_ids = [
            session_id
            for session_id, session in self._sessions.items()
            if not session.is_valid()
        ]
        for session_id in expired_ids:
            del self._sessions[session_id]
        return len(expired_ids)


class JwtCodec:
    """
    A compact HS256 JSON Web Token implementation for educational purposes.

    The access token is stateless: validation requires the signing secret but
    does not require looking up a server-side session. The refresh-token example
    below deliberately remains stateful so that revocation can be demonstrated.
    """

    def __init__(self, secret: bytes, issuer: str) -> None:
        if len(secret) < 32:
            raise ValueError("JWT signing secret must contain at least 32 bytes.")
        self.secret = secret
        self.issuer = issuer

    def _sign(self, signing_input: bytes) -> str:
        signature = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
        return b64url_encode(signature)

    def encode(
        self,
        subject: str,
        roles: set[str],
        lifetime: timedelta = timedelta(minutes=10),
    ) -> str:
        now = int(time.time())
        payload = {
            "iss": self.issuer,
            "sub": subject,
            "iat": now,
            "exp": now + int(lifetime.total_seconds()),
            "jti": secrets.token_urlsafe(16),
            "roles": sorted(roles),
        }

        header = {
            "alg": "HS256",
            "typ": "JWT",
        }

        header_part = b64url_encode(
            json.dumps(header, separators=(",", ":")).encode("utf-8")
        )
        payload_part = b64url_encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )

        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        signature = self._sign(signing_input)

        return f"{header_part}.{payload_part}.{signature}"

    def decode_and_verify(self, token: str) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Malformed token.")

        header_part, payload_part, signature_part = parts
        signing_input = f"{header_part}.{payload_part}".encode("ascii")

        expected_signature = self._sign(signing_input)
        if not hmac.compare_digest(signature_part, expected_signature):
            raise AuthenticationError("Invalid token signature.")

        try:
            header = json.loads(b64url_decode(header_part))
            payload = json.loads(b64url_decode(payload_part))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            raise AuthenticationError("Token encoding is invalid.")

        if header.get("alg") != "HS256":
            raise AuthenticationError("Unexpected signing algorithm.")

        if payload.get("iss") != self.issuer:
            raise AuthenticationError("Unexpected token issuer.")

        if not isinstance(payload.get("sub"), str):
            raise AuthenticationError("Token subject is missing.")

        exp = payload.get("exp")
        if not isinstance(exp, int) or int(time.time()) >= exp:
            raise AuthenticationError("Token has expired.")

        return payload


@dataclass
class RefreshTokenRecord:
    token_hash: str
    user_id: str
    expires_at: datetime
    revoked: bool = False
    replaced_by: Optional[str] = None


class RefreshTokenStore:
    """
    Refresh tokens are opaque random values. Only their hashes are stored,
    which prevents a database leak from directly exposing active tokens.
    """

    def __init__(self) -> None:
        self._records: dict[str, RefreshTokenRecord] = {}

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def issue(
        self,
        user_id: str,
        lifetime: timedelta = timedelta(days=30),
    ) -> str:
        token = secrets.token_urlsafe(48)
        token_hash = self._hash(token)

        self._records[token_hash] = RefreshTokenRecord(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=utc_now() + lifetime,
        )
        return token

    def rotate(self, token: str, lifetime: timedelta = timedelta(days=30)) -> str:
        token_hash = self._hash(token)
        record = self._records.get(token_hash)

        if record is None:
            raise AuthenticationError("Unknown refresh token.")

        if record.revoked:
            raise AuthenticationError("Refresh token has already been revoked.")

        if utc_now() >= record.expires_at:
            record.revoked = True
            raise AuthenticationError("Refresh token has expired.")

        record.revoked = True

        new_token = self.issue(record.user_id, lifetime)
        record.replaced_by = self._hash(new_token)
        return new_token

    def revoke(self, token: str) -> None:
        record = self._records.get(self._hash(token))
        if record:
            record.revoked = True


class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, window: timedelta = timedelta(minutes=5)):
        self.max_attempts = max_attempts
        self.window = window
        self._attempts: dict[str, list[datetime]] = {}

    def allow(self, key: str) -> bool:
        now = utc_now()
        cutoff = now - self.window

        recent = [
            timestamp
            for timestamp in self._attempts.get(key, [])
            if timestamp >= cutoff
        ]

        if len(recent) >= self.max_attempts:
            self._attempts[key] = recent
            return False

        recent.append(now)
        self._attempts[key] = recent
        return True

    def clear(self, key: str) -> None:
        self._attempts.pop(key, None)


class AuthenticationService:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.sessions = SessionStore()
        self.refresh_tokens = RefreshTokenStore()
        self.rate_limiter = LoginRateLimiter()
        self.jwt = JwtCodec(
            secret=secrets.token_bytes(32),
            issuer="repository-auth-demo",
        )

    def register(self, username: str, password: str, roles: set[str]) -> User:
        normalized = username.strip().lower()

        if not normalized:
            raise ValueError("Username cannot be empty.")

        if len(password) < 12:
            raise ValueError("Password must contain at least 12 characters.")

        if normalized in self.users:
            raise ValueError("Username already exists.")

        user = User(
            user_id=secrets.token_hex(8),
            username=normalized,
            password_hash=hash_password(password),
            roles=set(roles),
        )
        self.users[normalized] = user
        return user

    def password_login(
        self,
        username: str,
        password: str,
        ip_address: str,
        user_agent: str,
    ) -> dict[str, str]:
        normalized = username.strip().lower()
        rate_key = f"{normalized}:{ip_address}"

        if not self.rate_limiter.allow(rate_key):
            raise AuthenticationError("Too many authentication attempts.")

        user = self.users.get(normalized)

        if user is None or not user.active or not verify_password(
            password,
            user.password_hash if user else "",
        ):
            raise AuthenticationError("Invalid username or password.")

        self.rate_limiter.clear(rate_key)

        # Session identifiers are regenerated after successful authentication.
        # A new identifier prevents session-fixation attacks.
        session = self.sessions.create(
            user_id=user.user_id,
            lifetime=timedelta(hours=8),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        access_token = self.jwt.encode(
            subject=user.user_id,
            roles=user.roles,
            lifetime=timedelta(minutes=10),
        )

        refresh_token = self.refresh_tokens.issue(user.user_id)

        return {
            "session_id": session.session_id,
            "csrf_token": session.csrf_token,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def authenticate_session(self, session_id: str) -> User:
        session = self.sessions.get(session_id)
        if session is None:
            raise AuthenticationError("Invalid session.")

        user = next(
            (candidate for candidate in self.users.values() if candidate.user_id == session.user_id),
            None,
        )

        if user is None or not user.active:
            raise AuthenticationError("User is unavailable.")

        self.sessions.touch(session_id)
        return user

    def authenticate_access_token(self, token: str) -> User:
        claims = self.jwt.decode_and_verify(token)
        user_id = claims["sub"]

        user = next(
            (candidate for candidate in self.users.values() if candidate.user_id == user_id),
            None,
        )

        if user is None or not user.active:
            raise AuthenticationError("Token subject is not active.")

        return user

    def refresh(self, refresh_token: str) -> dict[str, str]:
        new_refresh_token = self.refresh_tokens.rotate(refresh_token)

        claims: Optional[RefreshTokenRecord] = None
        token_hash = RefreshTokenStore._hash(new_refresh_token)
        claims = self.refresh_tokens._records[token_hash]

        user = next(
            (candidate for candidate in self.users.values() if candidate.user_id == claims.user_id),
            None,
        )
        if user is None or not user.active:
            raise AuthenticationError("Refresh token belongs to an inactive user.")

        access_token = self.jwt.encode(
            subject=user.user_id,
            roles=user.roles,
            lifetime=timedelta(minutes=10),
        )

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        }

    def logout(self, session_id: str, refresh_token: str) -> None:
        self.sessions.revoke(session_id)
        self.refresh_tokens.revoke(refresh_token)

    def logout_all(self, user_id: str) -> int:
        return self.sessions.revoke_user_sessions(user_id)


def require_role(user: User, role: str) -> None:
    if role not in user.roles:
        raise AuthorizationError(
            f"User '{user.username}' lacks required role '{role}'."
        )


def demonstrate_password_authentication(service: AuthenticationService) -> User:
    print("\n=== Password authentication ===")

    user = service.register(
        username="alice@example.com",
        password="Correct-Horse-Battery-9!",
        roles={"user", "reviewer"},
    )

    print("Stored password representation:", user.password_hash[:45] + "...")
    print(
        "Correct password:",
        verify_password("Correct-Horse-Battery-9!", user.password_hash),
    )
    print(
        "Wrong password:",
        verify_password("wrong-password", user.password_hash),
    )

    return user


def demonstrate_session_flow(
    service: AuthenticationService,
    user: User,
) -> tuple[str, str]:
    print("\n=== Stateful session flow ===")

    credentials = service.password_login(
        username=user.username,
        password="Correct-Horse-Battery-9!",
        ip_address="203.0.113.10",
        user_agent="ExampleBrowser/1.0",
    )

    session_id = credentials["session_id"]

    authenticated_user = service.authenticate_session(session_id)
    print("Authenticated session owner:", authenticated_user.username)
    print("CSRF token generated:", credentials["csrf_token"][:16] + "...")

    require_role(authenticated_user, "reviewer")
    print("Authorization succeeded for reviewer role.")

    service.sessions.revoke(session_id)

    try:
        service.authenticate_session(session_id)
    except AuthenticationError as exc:
        print("Revoked session rejected:", exc)

    return credentials["access_token"], credentials["refresh_token"]


def demonstrate_token_flow(
    service: AuthenticationService,
    user: User,
    access_token: str,
    refresh_token: str,
) -> None:
    print("\n=== Access-token and refresh-token flow ===")

    token_user = service.authenticate_access_token(access_token)
    print("JWT subject resolved to:", token_user.username)

    refreshed = service.refresh(refresh_token)
    print("Rotated refresh token issued:", refreshed["refresh_token"][:16] + "...")
    print("New access token issued:", refreshed["access_token"][:16] + "...")

    try:
        # Rotation means the original refresh token cannot be replayed.
        service.refresh(refresh_token)
    except AuthenticationError as exc:
        print("Replay of old refresh token rejected:", exc)


def demonstrate_authorization(service: AuthenticationService) -> None:
    print("\n=== Authentication versus authorization ===")

    normal_user = service.register(
        username="bob@example.com",
        password="Longer-Password-123!",
        roles={"user"},
    )

    credentials = service.password_login(
        username=normal_user.username,
        password="Longer-Password-123!",
        ip_address="203.0.113.11",
        user_agent="ExampleBrowser/1.0",
    )

    authenticated = service.authenticate_access_token(credentials["access_token"])

    try:
        require_role(authenticated, "admin")
    except AuthorizationError as exc:
        print("Authenticated user denied by authorization policy:", exc)


def demonstrate_security_failures(service: AuthenticationService) -> None:
    print("\n=== Security failure handling ===")

    for attempt in range(1, 7):
        try:
            service.password_login(
                username="alice@example.com",
                password="wrong-password",
                ip_address="198.51.100.20",
                user_agent="SuspiciousClient/1.0",
            )
            print("Unexpected authentication success.")
        except AuthenticationError as exc:
            print(f"Attempt {attempt}: {exc}")

    try:
        service.authenticate_access_token("tampered.token.value")
    except AuthenticationError as exc:
        print("Malformed token rejected:", exc)


def demonstrate_cookie_policy() -> None:
    print("\n=== Secure cookie policy ===")

    cookie_attributes = {
        "Secure": True,
        "HttpOnly": True,
        "SameSite": "Lax",
        "Path": "/",
    }

    print(
        "A browser session cookie should normally use attributes:",
        json.dumps(cookie_attributes),
    )
    print(
        "Secure prevents ordinary HTTP transmission; HttpOnly blocks JavaScript "
        "access; SameSite reduces cross-site request risk."
    )


def main() -> None:
    service = AuthenticationService()

    user = demonstrate_password_authentication(service)
    access_token, refresh_token = demonstrate_session_flow(service, user)
    demonstrate_token_flow(service, user, access_token, refresh_token)
    demonstrate_authorization(service)
    demonstrate_security_failures(service)
    demonstrate_cookie_policy()

    print("\n=== Authentication model ===")
    print("Password -> authentication -> session or token -> authorization")
    print("Stateful sessions support server-side revocation and session inspection.")
    print("Short-lived access tokens reduce the exposure window of a leaked token.")
    print("Refresh-token rotation provides a stateful control point for long-lived credentials.")
    print("Authentication proves identity; authorization determines permitted actions.")


if __name__ == "__main__":
    main()
