import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Pattern;

/*
 * API Validation and Error Responses
 *
 * Enterprise-oriented Java 17 implementation.
 *
 * Compile:
 *   javac ApiValidation.java
 *
 * Run:
 *   java ApiValidation
 */

public class ApiValidation {

    enum ErrorCode {
        INVALID_JSON,
        VALIDATION_FAILED,
        AUTHENTICATION_REQUIRED,
        ACCESS_DENIED,
        RESOURCE_CONFLICT,
        RESOURCE_NOT_FOUND,
        INVALID_STATE,
        INTERNAL_ERROR
    }

    record FieldViolation(String field, String code, String message) {
        FieldViolation {
            Objects.requireNonNull(field);
            Objects.requireNonNull(code);
            Objects.requireNonNull(message);
        }
    }

    record ApiError(
        int status,
        ErrorCode code,
        String message,
        List<FieldViolation> details,
        String requestId
    ) {
        ApiError {
            details = List.copyOf(details);
            Objects.requireNonNull(requestId);
        }

        String toJson() {
            StringBuilder output = new StringBuilder();
            output.append("{\"error\":{")
                .append("\"code\":\"").append(escape(code.name())).append("\",")
                .append("\"message\":\"").append(escape(message)).append("\",")
                .append("\"request_id\":\"").append(escape(requestId)).append("\",")
                .append("\"details\":[");

            for (int index = 0; index < details.size(); index++) {
                FieldViolation detail = details.get(index);

                if (index > 0) {
                    output.append(',');
                }

                output.append("{")
                    .append("\"field\":\"").append(escape(detail.field())).append("\",")
                    .append("\"code\":\"").append(escape(detail.code())).append("\",")
                    .append("\"message\":\"").append(escape(detail.message())).append("\"")
                    .append("}");
            }

            return output.append("]}}").toString();
        }
    }

    static class ApiException extends RuntimeException {
        private final int status;
        private final ErrorCode code;
        private final List<FieldViolation> details;

        ApiException(
            int status,
            ErrorCode code,
            String message,
            List<FieldViolation> details
        ) {
            super(message);
            this.status = status;
            this.code = code;
            this.details = List.copyOf(details);
        }

        ApiError toError(String requestId) {
            return new ApiError(
                status,
                code,
                getMessage(),
                details,
                requestId
            );
        }
    }

    enum Permission {
        REGISTER_DEVICE,
        READ_DEVICE
    }

    record Principal(String subject, Set<Permission> permissions) {
        Principal {
            if (subject == null || subject.isBlank()) {
                throw new IllegalArgumentException("Principal subject is required.");
            }

            permissions = Set.copyOf(permissions);
        }

        boolean can(Permission permission) {
            return permissions.contains(permission);
        }
    }

    record DeviceCommand(
        String deviceName,
        String ownerEmail,
        int firmwareMajor
    ) {}

    record Device(
        long id,
        String deviceName,
        String ownerEmail,
        int firmwareMajor,
        String registeredBy
    ) {}

    static final class DeviceRequestValidator {
        private static final Pattern EMAIL =
            Pattern.compile("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$");

        private static final Set<String> ALLOWED_FIELDS =
            Set.of("deviceName", "ownerEmail", "firmwareMajor");

        DeviceCommand validate(Map<String, Object> input) {
            List<FieldViolation> errors = new ArrayList<>();

            for (String field : input.keySet()) {
                if (!ALLOWED_FIELDS.contains(field)) {
                    errors.add(new FieldViolation(
                        field,
                        "unknown_field",
                        "This field is not accepted."
                    ));
                }
            }

            String name = validateName(input, errors);
            String email = validateEmail(input, errors);
            Integer firmware = validateFirmware(input, errors);

            if (!errors.isEmpty()) {
                throw new ApiException(
                    422,
                    ErrorCode.VALIDATION_FAILED,
                    "The request failed validation.",
                    errors
                );
            }

            return new DeviceCommand(name, email, firmware);
        }

        private String validateName(
            Map<String, Object> input,
            List<FieldViolation> errors
        ) {
            Object raw = input.get("deviceName");

            if (raw == null) {
                errors.add(new FieldViolation(
                    "deviceName", "required", "Device name is required."
                ));
                return "";
            }

            if (!(raw instanceof String value)) {
                errors.add(new FieldViolation(
                    "deviceName", "invalid_type", "Expected a string."
                ));
                return "";
            }

            String name = value.strip();

            if (name.length() < 3 || name.length() > 64) {
                errors.add(new FieldViolation(
                    "deviceName",
                    "invalid_length",
                    "Device name must contain 3 to 64 characters."
                ));
            }

            if (name.chars().anyMatch(ch -> ch < 32 || ch == 127)) {
                errors.add(new FieldViolation(
                    "deviceName",
                    "invalid_characters",
                    "Control characters are not permitted."
                ));
            }

            return name;
        }

        private String validateEmail(
            Map<String, Object> input,
            List<FieldViolation> errors
        ) {
            Object raw = input.get("ownerEmail");

            if (raw == null) {
                errors.add(new FieldViolation(
                    "ownerEmail", "required", "Owner email is required."
                ));
                return "";
            }

            if (!(raw instanceof String value)) {
                errors.add(new FieldViolation(
                    "ownerEmail", "invalid_type", "Expected a string."
                ));
                return "";
            }

            String email = value.strip();

            if (email.length() > 254 || !EMAIL.matcher(email).matches()) {
                errors.add(new FieldViolation(
                    "ownerEmail",
                    "invalid_email",
                    "Provide a valid owner email address."
                ));
            }

            return email;
        }

        private Integer validateFirmware(
            Map<String, Object> input,
            List<FieldViolation> errors
        ) {
            Object raw = input.get("firmwareMajor");

            if (raw == null) {
                errors.add(new FieldViolation(
                    "firmwareMajor",
                    "required",
                    "Firmware major version is required."
                ));
                return 0;
            }

            // Integer is required. A JSON parser may produce a Double for
            // 4.0, which should not silently satisfy an integer field.
            if (!(raw instanceof Integer version)) {
                errors.add(new FieldViolation(
                    "firmwareMajor",
                    "invalid_type",
                    "Firmware major version must be an integer."
                ));
                return 0;
            }

            if (version < 1 || version > 99) {
                errors.add(new FieldViolation(
                    "firmwareMajor",
                    "out_of_range",
                    "Firmware major version must be between 1 and 99."
                ));
            }

            return version;
        }
    }

    static final class DeviceRepository {
        private final Map<String, Device> byNormalizedName = new HashMap<>();
        private long nextId = 1;

        synchronized Device register(DeviceCommand command, Principal principal) {
            String key = normalizeName(command.deviceName());

            if (byNormalizedName.containsKey(key)) {
                throw new ApiException(
                    409,
                    ErrorCode.RESOURCE_CONFLICT,
                    "A device with this name already exists.",
                    List.of(new FieldViolation(
                        "deviceName",
                        "already_exists",
                        "Device names must be unique."
                    ))
                );
            }

            Device device = new Device(
                nextId++,
                command.deviceName(),
                command.ownerEmail(),
                command.firmwareMajor(),
                principal.subject()
            );

            byNormalizedName.put(key, device);
            return device;
        }

        synchronized Optional<Device> findByName(String name) {
            return Optional.ofNullable(byNormalizedName.get(normalizeName(name)));
        }

        synchronized List<Device> all() {
            return Collections.unmodifiableList(
                new ArrayList<>(byNormalizedName.values())
            );
        }

        private String normalizeName(String name) {
            return name.strip().toLowerCase(Locale.ROOT);
        }
    }

    static final class DeviceRegistrationService {
        private final DeviceRequestValidator validator;
        private final DeviceRepository repository;

        DeviceRegistrationService(
            DeviceRequestValidator validator,
            DeviceRepository repository
        ) {
            this.validator = validator;
            this.repository = repository;
        }

        Device register(Map<String, Object> payload, Principal principal) {
            if (principal == null) {
                throw new ApiException(
                    401,
                    ErrorCode.AUTHENTICATION_REQUIRED,
                    "Authentication is required.",
                    List.of()
                );
            }

            if (!principal.can(Permission.REGISTER_DEVICE)) {
                throw new ApiException(
                    403,
                    ErrorCode.ACCESS_DENIED,
                    "The caller cannot register devices.",
                    List.of()
                );
            }

            DeviceCommand command = validator.validate(payload);
            return repository.register(command, principal);
        }

        Device find(String name, Principal principal) {
            if (principal == null) {
                throw new ApiException(
                    401,
                    ErrorCode.AUTHENTICATION_REQUIRED,
                    "Authentication is required.",
                    List.of()
                );
            }

            if (!principal.can(Permission.READ_DEVICE)) {
                throw new ApiException(
                    403,
                    ErrorCode.ACCESS_DENIED,
                    "The caller cannot read device records.",
                    List.of()
                );
            }

            return repository.findByName(name).orElseThrow(() ->
                new ApiException(
                    404,
                    ErrorCode.RESOURCE_NOT_FOUND,
                    "The requested device does not exist.",
                    List.of()
                )
            );
        }
    }

    record ApiResponse(int status, String body) {}

    static final class ApiBoundary {
        private final DeviceRegistrationService service;

        ApiBoundary(DeviceRegistrationService service) {
            this.service = service;
        }

        ApiResponse register(
            Map<String, Object> payload,
            Principal principal,
            String requestId
        ) {
            try {
                Device device = service.register(payload, principal);

                String body = "{\"data\":{"
                    + "\"id\":" + device.id() + ","
                    + "\"deviceName\":\"" + escape(device.deviceName()) + "\","
                    + "\"ownerEmail\":\"" + escape(device.ownerEmail()) + "\","
                    + "\"firmwareMajor\":" + device.firmwareMajor() + ","
                    + "\"registeredBy\":\"" + escape(device.registeredBy()) + "\""
                    + "},\"request_id\":\"" + escape(requestId) + "\"}";

                return new ApiResponse(201, body);
            } catch (ApiException exception) {
                return errorResponse(exception, requestId);
            } catch (RuntimeException exception) {
                // Operational logs should contain the exception and request ID.
                // Never expose internal exception messages to API consumers.
                return errorResponse(
                    new ApiException(
                        500,
                        ErrorCode.INTERNAL_ERROR,
                        "An unexpected error occurred.",
                        List.of()
                    ),
                    requestId
                );
            }
        }

        private ApiResponse errorResponse(
            ApiException exception,
            String requestId
        ) {
            return new ApiResponse(
                exception.status,
                exception.toError(requestId).toJson()
            );
        }
    }

    private static String escape(String value) {
        StringBuilder output = new StringBuilder();

        for (char ch : value.toCharArray()) {
            switch (ch) {
                case '"' -> output.append("\\\"");
                case '\\' -> output.append("\\\\");
                case '\b' -> output.append("\\b");
                case '\f' -> output.append("\\f");
                case '\n' -> output.append("\\n");
                case '\r' -> output.append("\\r");
                case '\t' -> output.append("\\t");
                default -> {
                    if (ch < 32) {
                        output.append(String.format("\\u%04x", (int) ch));
                    } else {
                        output.append(ch);
                    }
                }
            }
        }

        return output.toString();
    }

    private static Map<String, Object> payload(
        String name,
        String email,
        Object firmware
    ) {
        Map<String, Object> result = new HashMap<>();
        result.put("deviceName", name);
        result.put("ownerEmail", email);
        result.put("firmwareMajor", firmware);
        return result;
    }

    private static void print(String label, ApiResponse response) {
        System.out.println("\n" + label);
        System.out.println("HTTP " + response.status());
        System.out.println(response.body());
    }

    public static void main(String[] args) {
        DeviceRequestValidator validator = new DeviceRequestValidator();
        DeviceRepository repository = new DeviceRepository();
        DeviceRegistrationService service =
            new DeviceRegistrationService(validator, repository);
        ApiBoundary boundary = new ApiBoundary(service);

        Principal operator = new Principal(
            "operations-service",
            Set.of(Permission.REGISTER_DEVICE, Permission.READ_DEVICE)
        );

        Principal auditor = new Principal(
            "audit-service",
            Set.of(Permission.READ_DEVICE)
        );

        print(
            "Valid registration",
            boundary.register(
                payload("Pump Sensor A", "ops@example.com", 3),
                operator,
                "req-valid-001"
            )
        );

        print(
            "Invalid fields",
            boundary.register(
                payload("X", "invalid", 150),
                operator,
                "req-invalid-002"
            )
        );

        print(
            "Unknown field",
            boundary.register(
                Map.of(
                    "deviceName", "Pump Sensor B",
                    "ownerEmail", "ops2@example.com",
                    "firmwareMajor", 2,
                    "isAdministrator", true
                ),
                operator,
                "req-unknown-003"
            )
        );

        print(
            "Authorization failure",
            boundary.register(
                payload("Pump Sensor C", "ops3@example.com", 2),
                auditor,
                "req-forbidden-004"
            )
        );

        print(
            "Duplicate registration",
            boundary.register(
                payload("PUMP SENSOR A", "another@example.com", 4),
                operator,
                "req-conflict-005"
            )
        );

        print(
            "Missing authentication",
            boundary.register(
                payload("Pump Sensor D", "ops4@example.com", 2),
                null,
                "req-anonymous-006"
            )
        );

        try {
            Device missing = service.find("unknown-device", operator);
            System.out.println(missing);
        } catch (ApiException exception) {
            System.out.println("\nMissing resource");
            System.out.println(exception.toError("req-not-found-007").toJson());
        }
    }
}
