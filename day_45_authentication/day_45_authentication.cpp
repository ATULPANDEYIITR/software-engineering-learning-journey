#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <random>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using Clock = std::chrono::system_clock;
using TimePoint = Clock::time_point;

std::string generateId(const std::string& prefix) {
    static std::mt19937_64 generator{
        static_cast<std::uint64_t>(
            Clock::now().time_since_epoch().count()
        )
    };

    std::uniform_int_distribution<std::uint64_t> distribution;

    std::ostringstream output;
    output << prefix << "-" << std::hex << distribution(generator);
    return output.str();
}

std::string pseudoHash(const std::string& input) {
    /*
     * The program uses a deterministic digest-like representation only to keep
     * the C++17 case study dependency-free. It is not a password hashing
     * algorithm and must not replace Argon2, scrypt, or PBKDF2 in production.
     */
    std::hash<std::string> hasher;
    std::ostringstream output;
    output << std::hex << hasher("authentication-demo:" + input);
    return output.str();
}

enum class UserStatus {
    ACTIVE,
    DISABLED
};

enum class SessionState {
    ACTIVE,
    REVOKED,
    EXPIRED
};

enum class TokenState {
    ACTIVE,
    ROTATED,
    REVOKED,
    EXPIRED
};

enum class AuthenticationMethod {
    PASSWORD_SESSION,
    ACCESS_TOKEN,
    REFRESH_TOKEN
};

struct User {
    std::string id;
    std::string username;
    std::string passwordDigest;
    std::set<std::string> roles;
    UserStatus status{UserStatus::ACTIVE};
};

struct Session {
    std::string id;
    std::string userId;
    TimePoint createdAt;
    TimePoint expiresAt;
    SessionState state{SessionState::ACTIVE};
    std::string ipAddress;
};

struct AccessToken {
    std::string tokenId;
    std::string userId;
    TimePoint issuedAt;
    TimePoint expiresAt;
    std::set<std::string> roles;
    bool revoked{false};
};

struct RefreshToken {
    std::string tokenId;
    std::string userId;
    TimePoint issuedAt;
    TimePoint expiresAt;
    TokenState state{TokenState::ACTIVE};
    std::string replacementTokenId;
};

struct AuthenticationEvent {
    TimePoint timestamp;
    std::string userId;
    AuthenticationMethod method;
    bool successful;
    std::string reason;
};

class AuthenticationException : public std::runtime_error {
public:
    explicit AuthenticationException(const std::string& message)
        : std::runtime_error(message) {}
};

class AuthorizationException : public std::runtime_error {
public:
    explicit AuthorizationException(const std::string& message)
        : std::runtime_error(message) {}
};

class AuthenticationSystem {
private:
    std::unordered_map<std::string, User> users;
    std::unordered_map<std::string, Session> sessions;
    std::unordered_map<std::string, AccessToken> accessTokens;
    std::unordered_map<std::string, RefreshToken> refreshTokens;
    std::vector<AuthenticationEvent> events;

    bool expired(TimePoint expiry) const {
        return Clock::now() >= expiry;
    }

    void audit(
        const std::string& userId,
        AuthenticationMethod method,
        bool successful,
        const std::string& reason
    ) {
        events.push_back({
            Clock::now(),
            userId,
            method,
            successful,
            reason
        });
    }

    User& findUserById(const std::string& userId) {
        auto iterator = std::find_if(
            users.begin(),
            users.end(),
            [&](const auto& pair) {
                return pair.second.id == userId;
            }
        );

        if (iterator == users.end()) {
            throw AuthenticationException("User does not exist.");
        }

        return iterator->second;
    }

public:
    User& registerUser(
        const std::string& username,
        const std::string& password,
        const std::set<std::string>& roles
    ) {
        if (username.empty()) {
            throw std::invalid_argument("Username cannot be empty.");
        }

        if (password.size() < 12) {
            throw std::invalid_argument(
                "Password must contain at least 12 characters."
            );
        }

        for (const auto& pair : users) {
            if (pair.second.username == username) {
                throw std::invalid_argument("Username already exists.");
            }
        }

        User user{
            generateId("usr"),
            username,
            pseudoHash(password),
            roles,
            UserStatus::ACTIVE
        };

        auto [iterator, inserted] = users.emplace(user.id, user);

        if (!inserted) {
            throw std::runtime_error("Could not create user.");
        }

        return iterator->second;
    }

    std::string passwordLogin(
        const std::string& username,
        const std::string& password,
        const std::string& ipAddress
    ) {
        auto iterator = std::find_if(
            users.begin(),
            users.end(),
            [&](const auto& pair) {
                return pair.second.username == username;
            }
        );

        if (iterator == users.end()) {
            audit(
                "",
                AuthenticationMethod::PASSWORD_SESSION,
                false,
                "unknown user"
            );
            throw AuthenticationException("Invalid credentials.");
        }

        User& user = iterator->second;

        if (user.status != UserStatus::ACTIVE) {
            audit(
                user.id,
                AuthenticationMethod::PASSWORD_SESSION,
                false,
                "disabled account"
            );
            throw AuthenticationException("Account is disabled.");
        }

        if (pseudoHash(password) != user.passwordDigest) {
            audit(
                user.id,
                AuthenticationMethod::PASSWORD_SESSION,
                false,
                "incorrect password"
            );
            throw AuthenticationException("Invalid credentials.");
        }

        /*
         * A new server-side session is generated only after credentials are
         * verified. This prevents an attacker from fixing a session identifier
         * before the victim authenticates.
         */
        Session session{
            generateId("ses"),
            user.id,
            Clock::now(),
            Clock::now() + std::chrono::hours(8),
            SessionState::ACTIVE,
            ipAddress
        };

        sessions.emplace(session.id, session);

        audit(
            user.id,
            AuthenticationMethod::PASSWORD_SESSION,
            true,
            "password accepted"
        );

        return session.id;
    }

    User& authenticateSession(const std::string& sessionId) {
        auto iterator = sessions.find(sessionId);

        if (iterator == sessions.end()) {
            throw AuthenticationException("Unknown session.");
        }

        Session& session = iterator->second;

        if (session.state == SessionState::REVOKED) {
            throw AuthenticationException("Session is revoked.");
        }

        if (expired(session.expiresAt)) {
            session.state = SessionState::EXPIRED;
            throw AuthenticationException("Session has expired.");
        }

        User& user = findUserById(session.userId);

        if (user.status != UserStatus::ACTIVE) {
            throw AuthenticationException("Session owner is disabled.");
        }

        return user;
    }

    std::string issueAccessToken(const std::string& userId) {
        User& user = findUserById(userId);

        AccessToken token{
            generateId("atk"),
            user.id,
            Clock::now(),
            Clock::now() + std::chrono::minutes(10),
            user.roles,
            false
        };

        accessTokens.emplace(token.tokenId, token);
        return token.tokenId;
    }

    User& authenticateAccessToken(const std::string& tokenId) {
        auto iterator = accessTokens.find(tokenId);

        if (iterator == accessTokens.end()) {
            throw AuthenticationException("Unknown access token.");
        }

        AccessToken& token = iterator->second;

        if (token.revoked) {
            throw AuthenticationException("Access token is revoked.");
        }

        if (expired(token.expiresAt)) {
            throw AuthenticationException("Access token has expired.");
        }

        User& user = findUserById(token.userId);

        if (user.status != UserStatus::ACTIVE) {
            throw AuthenticationException("Token owner is disabled.");
        }

        return user;
    }

    std::string issueRefreshToken(const std::string& userId) {
        findUserById(userId);

        RefreshToken token{
            generateId("rtk"),
            userId,
            Clock::now(),
            Clock::now() + std::chrono::days(30),
            TokenState::ACTIVE,
            ""
        };

        refreshTokens.emplace(token.tokenId, token);
        return token.tokenId;
    }

    std::string rotateRefreshToken(const std::string& tokenId) {
        auto iterator = refreshTokens.find(tokenId);

        if (iterator == refreshTokens.end()) {
            throw AuthenticationException("Unknown refresh token.");
        }

        RefreshToken& oldToken = iterator->second;

        if (oldToken.state != TokenState::ACTIVE) {
            throw AuthenticationException(
                "Refresh token cannot be reused."
            );
        }

        if (expired(oldToken.expiresAt)) {
            oldToken.state = TokenState::EXPIRED;
            throw AuthenticationException("Refresh token has expired.");
        }

        std::string replacement = issueRefreshToken(oldToken.userId);

        oldToken.state = TokenState::ROTATED;
        oldToken.replacementTokenId = replacement;

        return replacement;
    }

    void revokeSession(const std::string& sessionId) {
        auto iterator = sessions.find(sessionId);

        if (iterator != sessions.end()) {
            iterator->second.state = SessionState::REVOKED;
        }
    }

    void revokeAllUserSessions(const std::string& userId) {
        for (auto& pair : sessions) {
            if (pair.second.userId == userId) {
                pair.second.state = SessionState::REVOKED;
            }
        }
    }

    void revokeAccessToken(const std::string& tokenId) {
        auto iterator = accessTokens.find(tokenId);

        if (iterator != accessTokens.end()) {
            iterator->second.revoked = true;
        }
    }

    void authorize(
        const User& user,
        const std::string& requiredRole
    ) const {
        if (!user.roles.contains(requiredRole)) {
            throw AuthorizationException(
                "Authenticated user lacks role: " + requiredRole
            );
        }
    }

    void disableUser(const std::string& userId) {
        User& user = findUserById(userId);
        user.status = UserStatus::DISABLED;

        /*
         * Disabling an account is stronger than merely rejecting the next
         * login. Existing stateful sessions are invalidated immediately.
         */
        revokeAllUserSessions(userId);

        for (auto& pair : accessTokens) {
            if (pair.second.userId == userId) {
                pair.second.revoked = true;
            }
        }
    }

    const std::vector<AuthenticationEvent>& auditLog() const {
        return events;
    }
};

std::string methodName(AuthenticationMethod method) {
    switch (method) {
        case AuthenticationMethod::PASSWORD_SESSION:
            return "password/session";
        case AuthenticationMethod::ACCESS_TOKEN:
            return "access token";
        case AuthenticationMethod::REFRESH_TOKEN:
            return "refresh token";
    }

    return "unknown";
}

int main() {
    AuthenticationSystem authentication;

    std::cout << "Repository administration authentication case study\n\n";

    User& administrator = authentication.registerUser(
        "admin@example.com",
        "Correct-Horse-Battery-9!",
        {"user", "reviewer", "administrator"}
    );

    User& developer = authentication.registerUser(
        "developer@example.com",
        "Long-Development-Password!",
        {"user"}
    );

    std::string sessionId = authentication.passwordLogin(
        developer.username,
        "Long-Development-Password!",
        "203.0.113.20"
    );

    std::cout << "Stateful session created: "
              << sessionId << "\n";

    User& sessionUser = authentication.authenticateSession(sessionId);

    std::cout << "Session authenticated for: "
              << sessionUser.username << "\n";

    std::string accessToken =
        authentication.issueAccessToken(sessionUser.id);

    User& tokenUser =
        authentication.authenticateAccessToken(accessToken);

    std::cout << "Short-lived access token accepted for: "
              << tokenUser.username << "\n";

    std::string refreshToken =
        authentication.issueRefreshToken(sessionUser.id);

    std::string rotatedRefreshToken =
        authentication.rotateRefreshToken(refreshToken);

    std::cout << "Refresh token rotated: "
              << rotatedRefreshToken << "\n";

    try {
        authentication.rotateRefreshToken(refreshToken);
    } catch (const AuthenticationException& exception) {
        std::cout << "Refresh-token replay rejected: "
                  << exception.what() << "\n";
    }

    try {
        authentication.authorize(sessionUser, "administrator");
    } catch (const AuthorizationException& exception) {
        std::cout << "Authorization decision: "
                  << exception.what() << "\n";
    }

    authentication.authorize(administrator, "administrator");
    std::cout << "Administrator authorization accepted.\n";

    authentication.disableUser(developer.id);

    try {
        authentication.authenticateSession(sessionId);
    } catch (const AuthenticationException& exception) {
        std::cout << "Existing session rejected after account disablement: "
                  << exception.what() << "\n";
    }

    try {
        authentication.authenticateAccessToken(accessToken);
    } catch (const AuthenticationException& exception) {
        std::cout << "Existing access token rejected after disablement: "
                  << exception.what() << "\n";
    }

    std::cout << "\nAuthentication audit events:\n";

    for (const AuthenticationEvent& event : authentication.auditLog()) {
        std::cout
            << "  user=" << event.userId
            << " method=" << methodName(event.method)
            << " success=" << std::boolalpha << event.successful
            << " reason=" << event.reason
            << "\n";
    }

    std::cout << "\nSecurity design observations:\n";
    std::cout
        << "  Stateful sessions allow immediate server-side revocation.\n"
        << "  Access tokens are short-lived and carry authorization claims.\n"
        << "  Refresh-token rotation makes replay detectable.\n"
        << "  Disabling a user invalidates existing authentication state.\n"
        << "  Authentication and authorization are evaluated separately.\n";

    return 0;
}
