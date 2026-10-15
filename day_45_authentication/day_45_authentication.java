import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

public class AuthenticationEnterpriseDemo {

    enum UserStatus {
        ACTIVE,
        DISABLED
    }

    enum SessionStatus {
        ACTIVE,
        REVOKED,
        EXPIRED
    }

    enum RefreshTokenStatus {
        ACTIVE,
        ROTATED,
        REVOKED,
        EXPIRED
    }

    enum AuthenticationMethod {
        PASSWORD,
        SESSION,
        ACCESS_TOKEN,
        REFRESH_TOKEN
    }

    record AuthenticationEvent(
        Instant timestamp,
        String userId,
        AuthenticationMethod method,
        boolean successful,
        String reason
    ) {}

    static final class User {
        private final String id;
        private final String username;
        private final String passwordHash;
        private final Set<String> roles;
        private UserStatus status;

        User(
            String id,
            String username,
            String passwordHash,
            Set<String> roles
        ) {
            this.id = id;
            this.username = username;
            this.passwordHash = passwordHash;
            this.roles = new HashSet<>(roles);
            this.status = UserStatus.ACTIVE;
        }

        String id() {
            return id;
        }

        String username() {
            return username;
        }

        String passwordHash() {
            return passwordHash;
        }

        Set<String> roles() {
            return Collections.unmodifiableSet(roles);
        }

        UserStatus status() {
            return status;
        }

        void disable() {
            status = UserStatus.DISABLED;
        }

        boolean hasRole(String role) {
            return roles.contains(role);
        }
    }

    static final class Session {
        private final String id;
        private final String userId;
        private final Instant createdAt;
        private final Instant expiresAt;
        private SessionStatus status;
        private Instant lastSeenAt;
        private final String csrfToken;

        Session(String userId, Duration lifetime) {
            this.id = UUID.randomUUID().toString();
            this.userId = userId;
            this.createdAt = Instant.now();
            this.expiresAt = createdAt.plus(lifetime);
            this.lastSeenAt = createdAt;
            this.status = SessionStatus.ACTIVE;
            this.csrfToken = UUID.randomUUID().toString();
        }

        String id() {
            return id;
        }

        String userId() {
            return userId;
        }

        String csrfToken() {
            return csrfToken;
        }

        boolean isUsable() {
            if (status != SessionStatus.ACTIVE) {
                return false;
            }

            if (Instant.now().isAfter(expiresAt)) {
                status = SessionStatus.EXPIRED;
                return false;
            }

            return true;
        }

        void touch() {
            lastSeenAt = Instant.now();
        }

        void revoke() {
            status = SessionStatus.REVOKED;
        }
    }

    static final class AccessToken {
        private final String tokenId;
        private final String userId;
        private final Instant issuedAt;
        private final Instant expiresAt;
        private final Set<String> roles;
        private boolean revoked;

        AccessToken(User user, Duration lifetime) {
            this.tokenId = UUID.randomUUID().toString();
            this.userId = user.id();
            this.issuedAt = Instant.now();
            this.expiresAt = issuedAt.plus(lifetime);
            this.roles = Set.copyOf(user.roles());
            this.revoked = false;
        }

        String tokenId() {
            return tokenId;
        }

        String userId() {
            return userId;
        }

        Set<String> roles() {
            return roles;
        }

        boolean isUsable() {
            return !revoked && Instant.now().isBefore(expiresAt);
        }

        void revoke() {
            revoked = true;
        }
    }

    static final class RefreshToken {
        private final String tokenId;
        private final String userId;
        private final Instant expiresAt;
        private RefreshTokenStatus status;

        RefreshToken(String userId, Duration lifetime) {
            this.tokenId = UUID.randomUUID().toString();
            this.userId = userId;
            this.expiresAt = Instant.now().plus(lifetime);
            this.status = RefreshTokenStatus.ACTIVE;
        }

        String tokenId() {
            return tokenId;
        }

        String userId() {
            return userId;
        }

        boolean isUsable() {
            if (status != RefreshTokenStatus.ACTIVE) {
                return false;
            }

            if (Instant.now().isAfter(expiresAt)) {
                status = RefreshTokenStatus.EXPIRED;
                return false;
            }

            return true;
        }

        void rotate() {
            status = RefreshTokenStatus.ROTATED;
        }

        void revoke() {
            status = RefreshTokenStatus.REVOKED;
        }
    }

    interface PasswordHasher {
        String hash(String password);

        boolean matches(String password, String encodedHash);
    }

    static final class DemoPasswordHasher implements PasswordHasher {

        /*
         * This deterministic digest is deliberately simple so the program can
         * run with only Java 17. Production systems should use a dedicated
         * password-hashing algorithm such as Argon2id, scrypt, or PBKDF2.
         */
        @Override
        public String hash(String password) {
            if (password == null || password.length() < 12) {
                throw new IllegalArgumentException(
                    "Password must contain at least 12 characters."
                );
            }

            return Integer.toHexString(
                Objects.hash("enterprise-auth-demo", password)
            );
        }

        @Override
        public boolean matches(String password, String encodedHash) {
            return hash(password).equals(encodedHash);
        }
    }

    static final class AuthenticationException
        extends RuntimeException {

        AuthenticationException(String message) {
            super(message);
        }
    }

    static final class AuthorizationException
        extends RuntimeException {

        AuthorizationException(String message) {
            super(message);
        }
    }

    static final class AuthenticationService {

        private final PasswordHasher passwordHasher;
        private final Map<String, User> usersByUsername = new HashMap<>();
        private final Map<String, User> usersById = new HashMap<>();
        private final Map<String, Session> sessions = new HashMap<>();
        private final Map<String, AccessToken> accessTokens = new HashMap<>();
        private final Map<String, RefreshToken> refreshTokens = new HashMap<>();
        private final List<AuthenticationEvent> auditEvents = new ArrayList<>();

        AuthenticationService(PasswordHasher passwordHasher) {
            this.passwordHasher = passwordHasher;
        }

        User register(
            String username,
            String password,
            Set<String> roles
        ) {
            String normalized = username.trim().toLowerCase();

            if (normalized.isBlank()) {
                throw new IllegalArgumentException(
                    "Username cannot be blank."
                );
            }

            if (usersByUsername.containsKey(normalized)) {
                throw new IllegalArgumentException(
                    "Username already exists."
                );
            }

            User user = new User(
                UUID.randomUUID().toString(),
                normalized,
                passwordHasher.hash(password),
                roles
            );

            usersByUsername.put(normalized, user);
            usersById.put(user.id(), user);

            audit(
                user.id(),
                AuthenticationMethod.PASSWORD,
                true,
                "account created"
            );

            return user;
        }

        AuthenticationResult login(
            String username,
            String password
        ) {
            String normalized = username.trim().toLowerCase();
            User user = usersByUsername.get(normalized);

            if (
                user == null ||
                user.status() != UserStatus.ACTIVE ||
                !passwordHasher.matches(
                    password,
                    user.passwordHash()
                )
            ) {
                audit(
                    user == null ? null : user.id(),
                    AuthenticationMethod.PASSWORD,
                    false,
                    "invalid credentials"
                );

                throw new AuthenticationException(
                    "Invalid credentials."
                );
            }

            /*
             * The session identifier is generated after credential verification.
             * This models session-ID regeneration at the authentication boundary.
             */
            Session session = new Session(
                user.id(),
                Duration.ofHours(8)
            );

            AccessToken accessToken = new AccessToken(
                user,
                Duration.ofMinutes(10)
            );

            RefreshToken refreshToken = new RefreshToken(
                user.id(),
                Duration.ofDays(30)
            );

            sessions.put(session.id(), session);
            accessTokens.put(accessToken.tokenId(), accessToken);
            refreshTokens.put(refreshToken.tokenId(), refreshToken);

            audit(
                user.id(),
                AuthenticationMethod.SESSION,
                true,
                "authenticated successfully"
            );

            return new AuthenticationResult(
                session.id(),
                session.csrfToken(),
                accessToken.tokenId(),
                refreshToken.tokenId()
            );
        }

        User authenticateSession(String sessionId) {
            Session session = sessions.get(sessionId);

            if (session == null || !session.isUsable()) {
                throw new AuthenticationException(
                    "Session is invalid, revoked, or expired."
                );
            }

            User user = usersById.get(session.userId());

            if (user == null || user.status() != UserStatus.ACTIVE) {
                throw new AuthenticationException(
                    "Session owner is inactive."
                );
            }

            session.touch();

            audit(
                user.id(),
                AuthenticationMethod.SESSION,
                true,
                "session accepted"
            );

            return user;
        }

        User authenticateAccessToken(String tokenId) {
            AccessToken token = accessTokens.get(tokenId);

            if (token == null || !token.isUsable()) {
                throw new AuthenticationException(
                    "Access token is invalid or expired."
                );
            }

            User user = usersById.get(token.userId());

            if (user == null || user.status() != UserStatus.ACTIVE) {
                throw new AuthenticationException(
                    "Access-token owner is inactive."
                );
            }

            return user;
        }

        String rotateRefreshToken(String tokenId) {
            RefreshToken current = refreshTokens.get(tokenId);

            if (current == null || !current.isUsable()) {
                throw new AuthenticationException(
                    "Refresh token cannot be used."
                );
            }

            User user = usersById.get(current.userId());

            if (user == null || user.status() != UserStatus.ACTIVE) {
                throw new AuthenticationException(
                    "Refresh-token owner is inactive."
                );
            }

            current.rotate();

            RefreshToken replacement = new RefreshToken(
                user.id(),
                Duration.ofDays(30)
            );

            refreshTokens.put(
                replacement.tokenId(),
                replacement
            );

            audit(
                user.id(),
                AuthenticationMethod.REFRESH_TOKEN,
                true,
                "refresh token rotated"
            );

            return replacement.tokenId();
        }

        void authorize(User user, String requiredRole) {
            if (!user.hasRole(requiredRole)) {
                throw new AuthorizationException(
                    "Required role is missing: " + requiredRole
                );
            }
        }

        void logout(String sessionId, String refreshTokenId) {
            Session session = sessions.get(sessionId);
            RefreshToken refreshToken =
                refreshTokens.get(refreshTokenId);

            if (session != null) {
                session.revoke();
            }

            if (refreshToken != null) {
                refreshToken.revoke();
            }
        }

        void disableUser(String userId) {
            User user = usersById.get(userId);

            if (user == null) {
                throw new IllegalArgumentException(
                    "Unknown user."
                );
            }

            user.disable();

            /*
             * Account disablement invalidates existing state rather than
             * waiting for session expiration. This gives administrators
             * an immediate containment mechanism.
             */
            sessions.values()
                .stream()
                .filter(session ->
                    session.userId().equals(userId)
                )
                .forEach(Session::revoke);

            accessTokens.values()
                .stream()
                .filter(token ->
                    token.userId().equals(userId)
                )
                .forEach(AccessToken::revoke);

            refreshTokens.values()
                .stream()
                .filter(token ->
                    token.userId().equals(userId)
                )
                .forEach(RefreshToken::revoke);
        }

        List<AuthenticationEvent> auditEvents() {
            return List.copyOf(auditEvents);
        }

        private void audit(
            String userId,
            AuthenticationMethod method,
            boolean successful,
            String reason
        ) {
            auditEvents.add(
                new AuthenticationEvent(
                    Instant.now(),
                    userId,
                    method,
                    successful,
                    reason
                )
            );
        }
    }

    record AuthenticationResult(
        String sessionId,
        String csrfToken,
        String accessTokenId,
        String refreshTokenId
    ) {}

    static void printPolicy() {
        System.out.println("Authentication policy");
        System.out.println(
            "Session: server-side state, eight-hour lifetime, revocable."
        );
        System.out.println(
            "Access token: short-lived identity and role representation."
        );
        System.out.println(
            "Refresh token: longer-lived credential that is rotated."
        );
        System.out.println(
            "Authorization: evaluated after identity authentication."
        );
    }

    public static void main(String[] args) {
        AuthenticationService service =
            new AuthenticationService(
                new DemoPasswordHasher()
            );

        printPolicy();

        User developer = service.register(
            "developer@example.com",
            "Long-Development-Password!",
            Set.of("user", "reviewer")
        );

        User administrator = service.register(
            "admin@example.com",
            "Correct-Horse-Battery-9!",
            Set.of("user", "administrator")
        );

        AuthenticationResult login = service.login(
            developer.username(),
            "Long-Development-Password!"
        );

        User sessionUser =
            service.authenticateSession(login.sessionId());

        System.out.println(
            "\nAuthenticated through session: "
            + sessionUser.username()
        );

        User tokenUser =
            service.authenticateAccessToken(
                login.accessTokenId()
            );

        System.out.println(
            "Authenticated through access token: "
            + tokenUser.username()
        );

        service.authorize(tokenUser, "reviewer");
        System.out.println(
            "Reviewer authorization accepted."
        );

        try {
            service.authorize(
                tokenUser,
                "administrator"
            );
        } catch (AuthorizationException exception) {
            System.out.println(
                "Administrator authorization rejected: "
                + exception.getMessage()
            );
        }

        String rotatedRefreshToken =
            service.rotateRefreshToken(
                login.refreshTokenId()
            );

        System.out.println(
            "Refresh token rotated: "
            + rotatedRefreshToken
        );

        try {
            service.rotateRefreshToken(
                login.refreshTokenId()
            );
        } catch (AuthenticationException exception) {
            System.out.println(
                "Old refresh-token replay rejected: "
                + exception.getMessage()
            );
        }

        service.disableUser(developer.id());

        try {
            service.authenticateSession(login.sessionId());
        } catch (AuthenticationException exception) {
            System.out.println(
                "Session rejected after account disablement: "
                + exception.getMessage()
            );
        }

        try {
            service.authenticateAccessToken(
                login.accessTokenId()
            );
        } catch (AuthenticationException exception) {
            System.out.println(
                "Access token rejected after account disablement: "
                + exception.getMessage()
            );
        }

        service.authorize(administrator, "administrator");

        System.out.println(
            "Administrator remains eligible for administrator policy."
        );

        System.out.println("\nAuthentication audit trail:");

        service.auditEvents().forEach(event ->
            System.out.println(
                event.timestamp()
                    + " method=" + event.method()
                    + " success=" + event.successful()
                    + " reason=" + event.reason()
            )
        );
    }
}
