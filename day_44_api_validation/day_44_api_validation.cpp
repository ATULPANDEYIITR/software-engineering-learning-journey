#include <algorithm>
#include <cctype>
#include <cstdint>
#include <iostream>
#include <map>
#include <optional>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * Repository-style API gateway case study.
 *
 * This C++17 program models an API request boundary for a service that accepts
 * device-registration requests. It evaluates request structure, field
 * constraints, authorization context, domain conflicts, and error mapping.
 *
 * Compile:
 *   g++ -std=c++17 -Wall -Wextra -pedantic api_validation.cpp -o api_validation
 *
 * Run:
 *   ./api_validation
 */

enum class ErrorCategory {
    MalformedRequest,
    Validation,
    Authentication,
    Authorization,
    Conflict,
    NotFound,
    Internal
};

struct FieldIssue {
    std::string field;
    std::string code;
    std::string message;
};

struct ApiError {
    int status;
    ErrorCategory category;
    std::string code;
    std::string message;
    std::vector<FieldIssue> details;
};

template <typename T>
struct Result {
    std::optional<T> value;
    std::optional<ApiError> error;

    static Result success(T item) {
        return {std::move(item), std::nullopt};
    }

    static Result failure(ApiError problem) {
        return {std::nullopt, std::move(problem)};
    }

    bool ok() const {
        return value.has_value();
    }
};

std::string trim(const std::string& value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return "";
    }

    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::string lowercase(std::string value) {
    std::transform(
        value.begin(),
        value.end(),
        value.begin(),
        [](unsigned char ch) {
            return static_cast<char>(std::tolower(ch));
        }
    );
    return value;
}

FieldIssue makeIssue(
    const std::string& field,
    const std::string& code,
    const std::string& message
) {
    return {field, code, message};
}

struct DeviceRegistration {
    std::string deviceName;
    std::string ownerEmail;
    int firmwareMajor;
};

class DeviceValidator {
public:
    Result<DeviceRegistration> validate(
        const std::map<std::string, std::string>& fields
    ) const {
        std::vector<FieldIssue> errors;

        const std::set<std::string> allowed = {
            "device_name",
            "owner_email",
            "firmware_major"
        };

        for (const auto& [key, value] : fields) {
            (void)value;

            if (allowed.find(key) == allowed.end()) {
                errors.push_back(makeIssue(
                    key,
                    "unknown_field",
                    "The field is not accepted."
                ));
            }
        }

        auto name = fields.find("device_name");
        auto email = fields.find("owner_email");
        auto firmware = fields.find("firmware_major");

        if (name == fields.end()) {
            errors.push_back(makeIssue(
                "device_name", "required", "Device name is required."
            ));
        }

        if (email == fields.end()) {
            errors.push_back(makeIssue(
                "owner_email", "required", "Owner email is required."
            ));
        }

        if (firmware == fields.end()) {
            errors.push_back(makeIssue(
                "firmware_major", "required", "Firmware version is required."
            ));
        }

        std::string normalizedName;
        std::string normalizedEmail;
        int firmwareVersion = 0;

        if (name != fields.end()) {
            normalizedName = trim(name->second);

            if (normalizedName.size() < 3 || normalizedName.size() > 64) {
                errors.push_back(makeIssue(
                    "device_name",
                    "invalid_length",
                    "Device name must contain 3 to 64 characters."
                ));
            }

            // Reject control bytes before the name enters logs or downstream
            // systems, where they could corrupt structured output.
            for (unsigned char ch : normalizedName) {
                if (ch < 32 || ch == 127) {
                    errors.push_back(makeIssue(
                        "device_name",
                        "invalid_characters",
                        "Control characters are not permitted."
                    ));
                    break;
                }
            }
        }

        if (email != fields.end()) {
            normalizedEmail = trim(email->second);
            static const std::regex emailPattern(
                R"(^[^@\s]+@[^@\s]+\.[^@\s]+$)"
            );

            if (
                normalizedEmail.size() > 254 ||
                !std::regex_match(normalizedEmail, emailPattern)
            ) {
                errors.push_back(makeIssue(
                    "owner_email",
                    "invalid_email",
                    "A valid owner email address is required."
                ));
            }
        }

        if (firmware != fields.end()) {
            const std::string raw = trim(firmware->second);

            // Require decimal digits only. Parsing through a wider integer
            // prevents overflow before the application checks its domain.
            if (
                raw.empty() ||
                !std::all_of(raw.begin(), raw.end(), [](unsigned char ch) {
                    return std::isdigit(ch) != 0;
                })
            ) {
                errors.push_back(makeIssue(
                    "firmware_major",
                    "invalid_integer",
                    "Firmware major version must be a decimal integer."
                ));
            } else {
                try {
                    std::size_t consumed = 0;
                    long long parsed = std::stoll(raw, &consumed);

                    if (consumed != raw.size() || parsed < 1 || parsed > 99) {
                        errors.push_back(makeIssue(
                            "firmware_major",
                            "out_of_range",
                            "Firmware major version must be between 1 and 99."
                        ));
                    } else {
                        firmwareVersion = static_cast<int>(parsed);
                    }
                } catch (const std::exception&) {
                    errors.push_back(makeIssue(
                        "firmware_major",
                        "out_of_range",
                        "Firmware major version is outside the supported range."
                    ));
                }
            }
        }

        if (!errors.empty()) {
            return Result<DeviceRegistration>::failure(ApiError{
                422,
                ErrorCategory::Validation,
                "validation_failed",
                "The registration request failed validation.",
                std::move(errors)
            });
        }

        return Result<DeviceRegistration>::success(DeviceRegistration{
            normalizedName,
            normalizedEmail,
            firmwareVersion
        });
    }
};

struct RequestContext {
    std::string principal;
    bool authenticated;
    bool mayRegisterDevices;
};

struct RegisteredDevice {
    std::uint64_t id;
    DeviceRegistration registration;
};

class DeviceRegistry {
private:
    std::unordered_map<std::string, RegisteredDevice> byName_;
    std::uint64_t nextId_ = 1;

public:
    Result<RegisteredDevice> registerDevice(
        const DeviceRegistration& registration
    ) {
        const std::string key = lowercase(registration.deviceName);

        if (byName_.find(key) != byName_.end()) {
            return Result<RegisteredDevice>::failure(ApiError{
                409,
                ErrorCategory::Conflict,
                "device_name_conflict",
                "A device with this name already exists.",
                {
                    makeIssue(
                        "device_name",
                        "already_exists",
                        "Device names must be unique."
                    )
                }
            });
        }

        RegisteredDevice device{nextId_++, registration};
        byName_.emplace(key, device);
        return Result<RegisteredDevice>::success(device);
    }

    Result<RegisteredDevice> find(const std::string& name) const {
        const auto found = byName_.find(lowercase(trim(name)));

        if (found == byName_.end()) {
            return Result<RegisteredDevice>::failure(ApiError{
                404,
                ErrorCategory::NotFound,
                "device_not_found",
                "The requested device does not exist.",
                {}
            });
        }

        return Result<RegisteredDevice>::success(found->second);
    }
};

struct ApiResponse {
    int status;
    std::string body;
};

std::string escapeJson(const std::string& input) {
    std::ostringstream output;

    for (unsigned char ch : input) {
        switch (ch) {
            case '"': output << "\\\""; break;
            case '\\': output << "\\\\"; break;
            case '\b': output << "\\b"; break;
            case '\f': output << "\\f"; break;
            case '\n': output << "\\n"; break;
            case '\r': output << "\\r"; break;
            case '\t': output << "\\t"; break;
            default:
                if (ch < 32) {
                    static const char* digits = "0123456789abcdef";
                    output << "\\u00"
                           << digits[(ch >> 4) & 0x0F]
                           << digits[ch & 0x0F];
                } else {
                    output << static_cast<char>(ch);
                }
        }
    }

    return output.str();
}

std::string errorCategoryName(ErrorCategory category) {
    switch (category) {
        case ErrorCategory::MalformedRequest: return "malformed_request";
        case ErrorCategory::Validation: return "validation";
        case ErrorCategory::Authentication: return "authentication";
        case ErrorCategory::Authorization: return "authorization";
        case ErrorCategory::Conflict: return "conflict";
        case ErrorCategory::NotFound: return "not_found";
        case ErrorCategory::Internal: return "internal";
    }

    return "internal";
}

ApiResponse serializeError(const ApiError& error) {
    std::ostringstream body;

    body << "{\"error\":{"
         << "\"code\":\"" << escapeJson(error.code) << "\","
         << "\"category\":\"" << errorCategoryName(error.category) << "\","
         << "\"message\":\"" << escapeJson(error.message) << "\","
         << "\"details\":[";

    for (std::size_t index = 0; index < error.details.size(); ++index) {
        const auto& item = error.details[index];

        if (index != 0) {
            body << ',';
        }

        body << "{"
             << "\"field\":\"" << escapeJson(item.field) << "\","
             << "\"code\":\"" << escapeJson(item.code) << "\","
             << "\"message\":\"" << escapeJson(item.message) << "\""
             << "}";
    }

    body << "]}}";

    return {error.status, body.str()};
}

ApiResponse serializeDevice(const RegisteredDevice& device) {
    std::ostringstream body;

    body << "{\"data\":{"
         << "\"id\":" << device.id << ','
         << "\"device_name\":\""
         << escapeJson(device.registration.deviceName) << "\","
         << "\"owner_email\":\""
         << escapeJson(device.registration.ownerEmail) << "\","
         << "\"firmware_major\":" << device.registration.firmwareMajor
         << "}}";

    return {201, body.str()};
}

class RegistrationEndpoint {
private:
    DeviceValidator validator_;
    DeviceRegistry registry_;

public:
    ApiResponse handle(
        const RequestContext& context,
        const std::map<std::string, std::string>& fields
    ) {
        // Authentication and authorization are independent of field validity.
        // A caller must not gain access merely by supplying valid data.
        if (!context.authenticated) {
            return serializeError(ApiError{
                401,
                ErrorCategory::Authentication,
                "authentication_required",
                "Authentication is required.",
                {}
            });
        }

        if (!context.mayRegisterDevices) {
            return serializeError(ApiError{
                403,
                ErrorCategory::Authorization,
                "registration_forbidden",
                "The caller cannot register devices.",
                {}
            });
        }

        auto validated = validator_.validate(fields);

        if (!validated.ok()) {
            return serializeError(*validated.error);
        }

        auto result = registry_.registerDevice(*validated.value);

        if (!result.ok()) {
            return serializeError(*result.error);
        }

        return serializeDevice(*result.value);
    }
};

void printResponse(const std::string& scenario, const ApiResponse& response) {
    std::cout << "\n" << scenario
              << "\nHTTP " << response.status
              << "\n" << response.body << "\n";
}

int main() {
    RegistrationEndpoint endpoint;

    const RequestContext authorized{"service-operator", true, true};
    const RequestContext anonymous{"", false, false};
    const RequestContext readOnly{"audit-reader", true, false};

    printResponse(
        "Valid registration",
        endpoint.handle(authorized, {
            {"device_name", "Plant Sensor A"},
            {"owner_email", "operator@example.com"},
            {"firmware_major", "4"}
        })
    );

    printResponse(
        "Malformed field values",
        endpoint.handle(authorized, {
            {"device_name", "X"},
            {"owner_email", "not-an-email"},
            {"firmware_major", "999"},
            {"admin", "true"}
        })
    );

    printResponse(
        "Authentication failure",
        endpoint.handle(anonymous, {
            {"device_name", "Plant Sensor B"},
            {"owner_email", "operator@example.com"},
            {"firmware_major", "4"}
        })
    );

    printResponse(
        "Authorization failure",
        endpoint.handle(readOnly, {
            {"device_name", "Plant Sensor B"},
            {"owner_email", "operator@example.com"},
            {"firmware_major", "4"}
        })
    );

    printResponse(
        "Duplicate device name",
        endpoint.handle(authorized, {
            {"device_name", "PLANT SENSOR A"},
            {"owner_email", "another@example.com"},
            {"firmware_major", "5"}
        })
    );

    DeviceRegistry registry;
    auto found = registry.find("missing-sensor");

    if (!found.ok()) {
        printResponse("Missing device", serializeError(*found.error));
    }

    return 0;
}
