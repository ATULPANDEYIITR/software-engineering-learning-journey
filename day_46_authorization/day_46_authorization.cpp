#include <algorithm>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

// Repository governance case study: an authorization engine evaluates access
// to production repositories, deployment operations, and restricted branches.
// Compile with: g++ -std=c++17 -Wall -Wextra -pedantic authorization.cpp -o authorization

enum class Effect { Allow, Deny };

enum class Reason {
    Granted,
    UnknownUser,
    InactiveUser,
    UnknownResource,
    MissingPermission,
    ExplicitDeny,
    OwnershipRequired,
    MfaRequired,
    TrustedNetworkRequired,
    ClassificationRestricted
};

std::string toString(Reason reason) {
    switch (reason) {
        case Reason::Granted: return "granted";
        case Reason::UnknownUser: return "unknown_user";
        case Reason::InactiveUser: return "inactive_user";
        case Reason::UnknownResource: return "unknown_resource";
        case Reason::MissingPermission: return "missing_permission";
        case Reason::ExplicitDeny: return "explicit_deny";
        case Reason::OwnershipRequired: return "ownership_required";
        case Reason::MfaRequired: return "mfa_required";
        case Reason::TrustedNetworkRequired: return "trusted_network_required";
        case Reason::ClassificationRestricted:
            return "classification_restricted";
    }
    return "unknown";
}

struct Permission {
    std::string resource;
    std::string action;

    bool matches(const std::string& requestedResource,
                 const std::string& requestedAction) const {
        return (resource == "*" || resource == requestedResource) &&
               (action == "*" || action == requestedAction);
    }
};

struct Role {
    std::string name;
    std::vector<Permission> permissions;
    std::set<std::string> inheritedRoles;
};

struct User {
    std::string id;
    std::string department;
    bool active{true};
    std::set<std::string> assignedRoles;
};

struct Resource {
    std::string id;
    std::string type;
    std::string ownerId;
    std::string environment;
    std::string classification;
};

struct RequestContext {
    std::string requestId;
    std::string sourceIp;
    bool mfaVerified{false};
    std::chrono::system_clock::time_point now;
};

struct Rule {
    std::string name;
    Effect effect;
    Permission permission;
    std::optional<std::string> requiredDepartment;
    std::optional<std::string> requiredEnvironment;
};

struct Decision {
    bool allowed;
    Reason reason;
    std::string matchedPolicy;
};

struct AuditRecord {
    std::string requestId;
    std::string userId;
    std::string resourceId;
    std::string action;
    bool allowed;
    Reason reason;
};

struct TemporaryGrant {
    std::string userId;
    Permission permission;
    std::chrono::system_clock::time_point expiresAt;
    std::string reason;
};

class GovernanceEngine {
public:
    void addRole(Role role) {
        if (role.name.empty() || roles_.count(role.name)) {
            throw std::invalid_argument("Role name must be unique and nonempty.");
        }
        const std::string name = role.name;
        roles_.emplace(name, std::move(role));
        try {
            validateRoleGraph();
        } catch (...) {
            roles_.erase(name);
            throw;
        }
    }

    void addUser(User user) {
        if (user.id.empty() || users_.count(user.id)) {
            throw std::invalid_argument("User ID must be unique and nonempty.");
        }
        for (const auto& role : user.assignedRoles) {
            if (!roles_.count(role)) {
                throw std::invalid_argument("User references an unknown role.");
            }
        }
        users_.emplace(user.id, std::move(user));
    }

    void addResource(Resource resource) {
        if (resource.id.empty() || resources_.count(resource.id)) {
            throw std::invalid_argument(
                "Resource ID must be unique and nonempty.");
        }
        if (!users_.count(resource.ownerId)) {
            throw std::invalid_argument("Resource owner must exist.");
        }
        resources_.emplace(resource.id, std::move(resource));
    }

    void addRule(Rule rule) {
        if (rule.name.empty()) {
            throw std::invalid_argument("Policy rule name is required.");
        }
        rules_.push_back(std::move(rule));
    }

    void addTemporaryGrant(TemporaryGrant grant) {
        if (!users_.count(grant.userId)) {
            throw std::invalid_argument("Grant references an unknown user.");
        }
        if (grant.reason.empty()) {
            throw std::invalid_argument("Grant reason is required.");
        }
        grants_.push_back(std::move(grant));
    }

    Decision authorize(const std::string& userId,
                       const std::string& resourceId,
                       const std::string& action,
                       const RequestContext& context) {
        Decision decision{false, Reason::UnknownUser, ""};
        const auto userIt = users_.find(userId);
        const auto resourceIt = resources_.find(resourceId);

        if (context.requestId.empty() || context.sourceIp.empty()) {
            decision = {false, Reason::MissingPermission, "invalid-context"};
        } else if (userIt == users_.end()) {
            decision = {false, Reason::UnknownUser, ""};
        } else if (!userIt->second.active) {
            decision = {false, Reason::InactiveUser, ""};
        } else if (resourceIt == resources_.end()) {
            decision = {false, Reason::UnknownResource, ""};
        } else {
            decision = evaluate(
                userIt->second, resourceIt->second, action, context);
        }

        // Denials are audited as carefully as successful decisions.
        audit_.push_back(AuditRecord{
            context.requestId, userId, resourceId, action,
            decision.allowed, decision.reason
        });
        return decision;
    }

    void printAudit() const {
        std::cout << "\nAuthorization audit\n";
        for (const auto& record : audit_) {
            std::cout << record.requestId << " user=" << record.userId
                      << " resource=" << record.resourceId
                      << " action=" << record.action
                      << " decision=" << (record.allowed ? "ALLOW" : "DENY")
                      << " reason=" << toString(record.reason) << '\n';
        }
    }

private:
    std::map<std::string, Role> roles_;
    std::map<std::string, User> users_;
    std::map<std::string, Resource> resources_;
    std::vector<Rule> rules_;
    std::vector<TemporaryGrant> grants_;
    std::vector<AuditRecord> audit_;

    void validateRoleGraph() const {
        std::set<std::string> visiting;
        std::set<std::string> visited;

        auto visit = [&](const auto& self, const std::string& name) -> void {
            if (!roles_.count(name)) {
                throw std::invalid_argument("Unknown inherited role: " + name);
            }
            if (visiting.count(name)) {
                throw std::invalid_argument("Role inheritance cycle detected.");
            }
            if (visited.count(name)) return;

            visiting.insert(name);
            for (const auto& parent : roles_.at(name).inheritedRoles) {
                self(self, parent);
            }
            visiting.erase(name);
            visited.insert(name);
        };

        for (const auto& [name, role] : roles_) {
            (void)role;
            visit(visit, name);
        }
    }

    std::vector<Permission> effectivePermissions(const User& user) const {
        std::vector<Permission> result;
        std::set<std::string> visited;

        auto collect = [&](const auto& self, const std::string& name) -> void {
            if (!visited.insert(name).second) return;
            const auto roleIt = roles_.find(name);
            if (roleIt == roles_.end()) {
                throw std::logic_error("Invalid role assignment.");
            }

            result.insert(
                result.end(),
                roleIt->second.permissions.begin(),
                roleIt->second.permissions.end());

            for (const auto& parent : roleIt->second.inheritedRoles) {
                self(self, parent);
            }
        };

        for (const auto& role : user.assignedRoles) collect(collect, role);
        return result;
    }

    Decision evaluate(const User& user,
                      const Resource& resource,
                      const std::string& action,
                      const RequestContext& context) const {
        const auto permissions = effectivePermissions(user);

        bool permitted = std::any_of(
            permissions.begin(), permissions.end(),
            [&](const Permission& p) {
                return p.matches(resource.type, action);
            });

        for (const auto& grant : grants_) {
            if (grant.userId == user.id &&
                context.now < grant.expiresAt &&
                grant.permission.matches(resource.type, action)) {
                permitted = true;
            }
        }

        // Explicit deny rules are evaluated before any allow rule.
        for (const auto& rule : rules_) {
            if (rule.effect != Effect::Deny ||
                !rule.permission.matches(resource.type, action)) {
                continue;
            }

            const bool departmentMatches =
                !rule.requiredDepartment ||
                *rule.requiredDepartment == user.department;
            const bool environmentMatches =
                !rule.requiredEnvironment ||
                *rule.requiredEnvironment == resource.environment;

            if (departmentMatches && environmentMatches) {
                return {false, Reason::ExplicitDeny, rule.name};
            }
        }

        if (!permitted) {
            return {false, Reason::MissingPermission, ""};
        }

        if (resource.classification == "restricted" &&
            user.department != "security" &&
            action == "read") {
            return {false, Reason::ClassificationRestricted, ""};
        }

        if (resource.environment == "production" &&
            (action == "deploy" || action == "delete")) {
            if (!context.mfaVerified) {
                return {false, Reason::MfaRequired, ""};
            }
            if (context.sourceIp.rfind("10.", 0) != 0) {
                return {false, Reason::TrustedNetworkRequired, ""};
            }
        }

        return {true, Reason::Granted, "role-or-temporary-grant"};
    }
};

int main() {
    using Clock = std::chrono::system_clock;
    GovernanceEngine engine;

    try {
        engine.addRole(Role{
            "reader",
            {{"repository", "read"}, {"pull_request", "read"}},
            {}
        });
        engine.addRole(Role{
            "developer",
            {{"repository", "write"}, {"pull_request", "create"}},
            {"reader"}
        });
        engine.addRole(Role{
            "reviewer",
            {{"pull_request", "review"}, {"pull_request", "approve"}},
            {"reader"}
        });
        engine.addRole(Role{
            "release_manager",
            {{"repository", "deploy"}, {"repository", "delete"}},
            {}
        });

        engine.addUser(User{"maya", "engineering", true, {"developer"}});
        engine.addUser(User{"noah", "security", true, {"reviewer"}});
        engine.addUser(User{"olivia", "platform", true, {"release_manager"}});
        engine.addUser(User{"inactive-account", "engineering", false, {"reader"}});

        engine.addResource(Resource{
            "payments-service", "repository", "maya",
            "production", "restricted"
        });
        engine.addResource(Resource{
            "pr-842", "pull_request", "maya",
            "development", "internal"
        });

        engine.addRule(Rule{
            "platform-cannot-delete-production",
            Effect::Deny,
            {"repository", "delete"},
            std::string("platform"),
            std::string("production")
        });

        const auto now = Clock::now();
        engine.addTemporaryGrant(TemporaryGrant{
            "maya",
            {"repository", "deploy"},
            now + std::chrono::minutes(10),
            "Incident-approved release window"
        });

        const std::vector<std::tuple<std::string, std::string, std::string,
                                     std::string, bool>> requests = {
            {"maya", "payments-service", "write", "10.4.0.12", true},
            {"noah", "pr-842", "approve", "10.4.0.13", true},
            {"olivia", "payments-service", "deploy", "10.4.0.14", true},
            {"olivia", "payments-service", "deploy", "198.51.100.4", true},
            {"olivia", "payments-service", "delete", "10.4.0.14", true},
            {"inactive-account", "payments-service", "read", "10.4.0.12", true},
            {"unknown-user", "payments-service", "read", "10.4.0.12", true}
        };

        int sequence = 0;
        for (const auto& [user, resource, action, ip, mfa] : requests) {
            RequestContext context{
                "case-" + std::to_string(++sequence), ip, mfa, now
            };
            const Decision decision =
                engine.authorize(user, resource, action, context);

            std::cout << context.requestId << ": " << user << " -> "
                      << (decision.allowed ? "ALLOW" : "DENY")
                      << " (" << toString(decision.reason) << ")\n";
        }

        engine.printAudit();
    } catch (const std::exception& error) {
        std::cerr << "Governance configuration error: "
                  << error.what() << '\n';
        return 1;
    }

    return 0;
}
