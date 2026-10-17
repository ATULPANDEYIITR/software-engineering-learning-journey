import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/*
 * Enterprise API contract governance.
 *
 * Java 17 or later:
 *   javac ApiContractGovernance.java
 *   java ApiContractGovernance
 *
 * This implementation models API operations, schema rules, compatibility
 * findings, security requirements, and release eligibility without external
 * dependencies. It does not attempt to implement the entire OpenAPI standard.
 */

public class ApiContractGovernance {

    enum HttpMethod {
        GET, POST, PUT, PATCH, DELETE
    }

    enum FindingSeverity {
        ERROR, WARNING
    }

    enum ReleaseState {
        DRAFT, VALIDATING, APPROVED, REJECTED
    }

    enum SchemaType {
        OBJECT, ARRAY, STRING, INTEGER, NUMBER, BOOLEAN
    }

    record ApiVersion(int major, int minor, int patch)
            implements Comparable<ApiVersion> {

        ApiVersion {
            if (major < 0 || minor < 0 || patch < 0) {
                throw new IllegalArgumentException(
                        "Version components cannot be negative");
            }
        }

        static ApiVersion parse(String text) {
            String[] parts = text.split("\\.", -1);
            if (parts.length != 3) {
                throw new IllegalArgumentException(
                        "Version must use MAJOR.MINOR.PATCH");
            }

            try {
                return new ApiVersion(
                        Integer.parseInt(parts[0]),
                        Integer.parseInt(parts[1]),
                        Integer.parseInt(parts[2]));
            } catch (NumberFormatException exception) {
                throw new IllegalArgumentException(
                        "Version components must be integers", exception);
            }
        }

        @Override
        public int compareTo(ApiVersion other) {
            int result = Integer.compare(major, other.major);
            if (result == 0) {
                result = Integer.compare(minor, other.minor);
            }
            if (result == 0) {
                result = Integer.compare(patch, other.patch);
            }
            return result;
        }

        @Override
        public String toString() {
            return major + "." + minor + "." + patch;
        }
    }

    record Finding(
            FindingSeverity severity,
            String code,
            String message) {
        Finding {
            Objects.requireNonNull(severity);
            Objects.requireNonNull(code);
            Objects.requireNonNull(message);
        }
    }

    record SchemaField(
            SchemaType type,
            boolean required,
            Set<String> enumValues,
            Integer minimumLength,
            Integer maximumLength) {

        SchemaField {
            Objects.requireNonNull(type);
            enumValues = Set.copyOf(enumValues);

            if (minimumLength != null && minimumLength < 0) {
                throw new IllegalArgumentException(
                        "Minimum string length cannot be negative");
            }
            if (maximumLength != null && maximumLength < 0) {
                throw new IllegalArgumentException(
                        "Maximum string length cannot be negative");
            }
            if (minimumLength != null && maximumLength != null
                    && minimumLength > maximumLength) {
                throw new IllegalArgumentException(
                        "Minimum length exceeds maximum length");
            }
        }
    }

    static final class ObjectSchema {
        private final Map<String, SchemaField> fields;
        private final boolean allowAdditionalProperties;

        ObjectSchema(
                Map<String, SchemaField> fields,
                boolean allowAdditionalProperties) {
            this.fields = Collections.unmodifiableMap(
                    new LinkedHashMap<>(fields));
            this.allowAdditionalProperties = allowAdditionalProperties;
        }

        Map<String, SchemaField> fields() {
            return fields;
        }

        List<Finding> validate(Map<String, Object> payload) {
            List<Finding> findings = new ArrayList<>();

            for (Map.Entry<String, SchemaField> entry : fields.entrySet()) {
                String name = entry.getKey();
                SchemaField field = entry.getValue();

                if (!payload.containsKey(name)) {
                    if (field.required()) {
                        findings.add(new Finding(
                                FindingSeverity.ERROR,
                                "REQUIRED_FIELD_MISSING",
                                "Required property '" + name + "' is missing"));
                    }
                    continue;
                }

                Object value = payload.get(name);
                if (!matchesType(value, field.type())) {
                    findings.add(new Finding(
                            FindingSeverity.ERROR,
                            "FIELD_TYPE_MISMATCH",
                            "Property '" + name + "' has an incompatible type"));
                    continue;
                }

                if (value instanceof String text) {
                    if (field.minimumLength() != null
                            && text.length() < field.minimumLength()) {
                        findings.add(new Finding(
                                FindingSeverity.ERROR,
                                "STRING_TOO_SHORT",
                                "Property '" + name + "' is too short"));
                    }

                    if (field.maximumLength() != null
                            && text.length() > field.maximumLength()) {
                        findings.add(new Finding(
                                FindingSeverity.ERROR,
                                "STRING_TOO_LONG",
                                "Property '" + name + "' is too long"));
                    }

                    if (!field.enumValues().isEmpty()
                            && !field.enumValues().contains(text)) {
                        findings.add(new Finding(
                                FindingSeverity.ERROR,
                                "ENUM_VALUE_INVALID",
                                "Property '" + name + "' is not an allowed value"));
                    }
                }
            }

            if (!allowAdditionalProperties) {
                for (String supplied : payload.keySet()) {
                    if (!fields.containsKey(supplied)) {
                        findings.add(new Finding(
                                FindingSeverity.ERROR,
                                "UNKNOWN_PROPERTY",
                                "Property '" + supplied + "' is not documented"));
                    }
                }
            }

            return findings;
        }

        private static boolean matchesType(Object value, SchemaType type) {
            return switch (type) {
                case OBJECT -> value instanceof Map<?, ?>;
                case ARRAY -> value instanceof List<?>;
                case STRING -> value instanceof String;
                case INTEGER -> value instanceof Integer
                        || value instanceof Long;
                case NUMBER -> value instanceof Number;
                case BOOLEAN -> value instanceof Boolean;
            };
        }
    }

    record ApiOperation(
            String operationId,
            HttpMethod method,
            String path,
            Set<Integer> responses,
            ObjectSchema requestSchema,
            boolean authenticationRequired) {

        ApiOperation {
            if (operationId == null || operationId.isBlank()) {
                throw new IllegalArgumentException(
                        "operationId must not be blank");
            }
            Objects.requireNonNull(method);
            if (path == null || !path.startsWith("/")) {
                throw new IllegalArgumentException(
                        "OpenAPI path must start with '/'");
            }
            responses = Set.copyOf(responses);
            if (responses.isEmpty()) {
                throw new IllegalArgumentException(
                        "Every operation must document at least one response");
            }
        }
    }

    record ImplementationEvidence(
            String operationId,
            Set<Integer> emittedStatuses,
            Set<String> acceptedFields,
            boolean authenticationEnforced) {

        ImplementationEvidence {
            Objects.requireNonNull(operationId);
            emittedStatuses = Set.copyOf(emittedStatuses);
            acceptedFields = Set.copyOf(acceptedFields);
        }
    }

    record GovernancePolicy(
            boolean requireContractTests,
            boolean requireSchemaValidation,
            boolean requireSecurityReview,
            boolean requireMajorVersionForBreakingChanges) {
    }

    static final class ApiRelease {
        private final ApiVersion currentVersion;
        private final ApiVersion previousVersion;
        private final List<ApiOperation> operations;
        private final List<ImplementationEvidence> evidence;
        private final boolean breakingChange;
        private final boolean schemaValidationPassed;
        private final boolean contractTestsPassed;
        private final boolean securityReviewPassed;

        ApiRelease(
                ApiVersion currentVersion,
                ApiVersion previousVersion,
                List<ApiOperation> operations,
                List<ImplementationEvidence> evidence,
                boolean breakingChange,
                boolean schemaValidationPassed,
                boolean contractTestsPassed,
                boolean securityReviewPassed) {
            this.currentVersion = Objects.requireNonNull(currentVersion);
            this.previousVersion = Objects.requireNonNull(previousVersion);
            this.operations = List.copyOf(operations);
            this.evidence = List.copyOf(evidence);
            this.breakingChange = breakingChange;
            this.schemaValidationPassed = schemaValidationPassed;
            this.contractTestsPassed = contractTestsPassed;
            this.securityReviewPassed = securityReviewPassed;
        }
    }

    static final class ReleaseGovernanceService {
        private final GovernancePolicy policy;

        ReleaseGovernanceService(GovernancePolicy policy) {
            this.policy = Objects.requireNonNull(policy);
        }

        List<Finding> evaluate(ApiRelease release) {
            List<Finding> findings = new ArrayList<>();

            if (policy.requireSchemaValidation()
                    && !release.schemaValidationPassed) {
                findings.add(new Finding(
                        FindingSeverity.ERROR,
                        "OPENAPI_VALIDATION_FAILED",
                        "The OpenAPI artifact did not pass validation"));
            }

            if (policy.requireContractTests()
                    && !release.contractTestsPassed) {
                findings.add(new Finding(
                        FindingSeverity.ERROR,
                        "CONTRACT_TESTS_FAILED",
                        "Runtime contract tests have not passed"));
            }

            if (policy.requireSecurityReview()
                    && !release.securityReviewPassed) {
                findings.add(new Finding(
                        FindingSeverity.ERROR,
                        "SECURITY_REVIEW_FAILED",
                        "Security review is incomplete"));
            }

            if (policy.requireMajorVersionForBreakingChanges()
                    && release.breakingChange
                    && release.currentVersion.major()
                    <= release.previousVersion.major()) {
                findings.add(new Finding(
                        FindingSeverity.ERROR,
                        "BREAKING_VERSION_CHANGE",
                        "Breaking changes require a higher major version"));
            }

            Map<String, ApiOperation> operationsById = new HashMap<>();
            for (ApiOperation operation : release.operations) {
                if (operationsById.putIfAbsent(
                        operation.operationId(), operation) != null) {
                    findings.add(new Finding(
                            FindingSeverity.ERROR,
                            "DUPLICATE_OPERATION_ID",
                            "Duplicate operationId: " + operation.operationId()));
                }
            }

            Map<String, ImplementationEvidence> evidenceById = new HashMap<>();
            for (ImplementationEvidence evidence : release.evidence) {
                if (evidenceById.putIfAbsent(
                        evidence.operationId(), evidence) != null) {
                    findings.add(new Finding(
                            FindingSeverity.ERROR,
                            "DUPLICATE_EVIDENCE",
                            "Duplicate evidence for " + evidence.operationId()));
                }
            }

            for (ApiOperation operation : release.operations) {
                ImplementationEvidence evidence =
                        evidenceById.get(operation.operationId());

                if (evidence == null) {
                    findings.add(new Finding(
                            FindingSeverity.ERROR,
                            "IMPLEMENTATION_NOT_VERIFIED",
                            operation.operationId()
                                    + " has no implementation evidence"));
                    continue;
                }

                for (Integer status : evidence.emittedStatuses()) {
                    if (!operation.responses().contains(status)) {
                        findings.add(new Finding(
                                FindingSeverity.ERROR,
                                "UNDOCUMENTED_HTTP_STATUS",
                                operation.operationId()
                                        + " emits undocumented HTTP "
                                        + status));
                    }
                }

                for (Integer status : operation.responses()) {
                    if (!evidence.emittedStatuses().contains(status)) {
                        findings.add(new Finding(
                                FindingSeverity.WARNING,
                                "UNTESTED_RESPONSE",
                                operation.operationId()
                                        + " documents HTTP " + status
                                        + " without implementation evidence"));
                    }
                }

                if (operation.authenticationRequired()
                        && !evidence.authenticationEnforced()) {
                    findings.add(new Finding(
                            FindingSeverity.ERROR,
                            "AUTHENTICATION_MISMATCH",
                            operation.operationId()
                                    + " requires authentication but the runtime "
                                    + "does not demonstrate enforcement"));
                }

                if (operation.requestSchema() != null) {
                    Set<String> documentedFields =
                            operation.requestSchema().fields().keySet();

                    for (String field : evidence.acceptedFields()) {
                        if (!documentedFields.contains(field)) {
                            findings.add(new Finding(
                                    FindingSeverity.ERROR,
                                    "UNDOCUMENTED_FIELD",
                                    operation.operationId()
                                            + " accepts undocumented field '"
                                            + field + "'"));
                        }
                    }
                }
            }

            for (ImplementationEvidence evidence : release.evidence) {
                if (!operationsById.containsKey(evidence.operationId())) {
                    findings.add(new Finding(
                            FindingSeverity.ERROR,
                            "UNDOCUMENTED_OPERATION",
                            "Runtime operation has no contract: "
                                    + evidence.operationId()));
                }
            }

            return findings;
        }

        boolean isEligible(ApiRelease release) {
            return evaluate(release).stream()
                    .noneMatch(f -> f.severity() == FindingSeverity.ERROR);
        }
    }

    static final class ReleaseWorkflow {
        private ReleaseState state = ReleaseState.DRAFT;

        ReleaseState state() {
            return state;
        }

        void beginValidation() {
            requireState(ReleaseState.DRAFT);
            state = ReleaseState.VALIDATING;
        }

        void approve(List<Finding> findings) {
            requireState(ReleaseState.VALIDATING);
            boolean errors = findings.stream()
                    .anyMatch(f -> f.severity() == FindingSeverity.ERROR);
            state = errors ? ReleaseState.REJECTED : ReleaseState.APPROVED;
        }

        void reopenForCorrection() {
            if (state != ReleaseState.REJECTED) {
                throw new IllegalStateException(
                        "Only a rejected release can be reopened for correction");
            }
            state = ReleaseState.DRAFT;
        }

        private void requireState(ReleaseState expected) {
            if (state != expected) {
                throw new IllegalStateException(
                        "Expected state " + expected + " but was " + state);
            }
        }
    }

    private static ObjectSchema createIncidentSchema() {
        Map<String, SchemaField> fields = new LinkedHashMap<>();
        fields.put("title", new SchemaField(
                SchemaType.STRING, true, Set.of(), 5, 120));
        fields.put("severity", new SchemaField(
                SchemaType.STRING, true,
                Set.of("low", "medium", "high", "critical"), null, null));
        fields.put("description", new SchemaField(
                SchemaType.STRING, false, Set.of(), 0, 4000));
        return new ObjectSchema(fields, false);
    }

    private static ApiRelease buildRelease() {
        ObjectSchema createIncident = createIncidentSchema();

        List<ApiOperation> operations = List.of(
                new ApiOperation(
                        "listIncidents",
                        HttpMethod.GET,
                        "/incidents",
                        Set.of(200, 401),
                        null,
                        true),
                new ApiOperation(
                        "createIncident",
                        HttpMethod.POST,
                        "/incidents",
                        Set.of(201, 400, 401, 409),
                        createIncident,
                        true),
                new ApiOperation(
                        "getIncident",
                        HttpMethod.GET,
                        "/incidents/{incidentId}",
                        Set.of(200, 400, 401, 404),
                        null,
                        true)
        );

        List<ImplementationEvidence> evidence = List.of(
                new ImplementationEvidence(
                        "listIncidents",
                        Set.of(200, 401),
                        Set.of(),
                        true),
                new ImplementationEvidence(
                        "createIncident",
                        Set.of(201, 400, 401, 409),
                        Set.of("title", "severity", "description"),
                        true),
                new ImplementationEvidence(
                        "getIncident",
                        Set.of(200, 400, 401, 404),
                        Set.of(),
                        true)
        );

        return new ApiRelease(
                ApiVersion.parse("3.1.0"),
                ApiVersion.parse("3.0.2"),
                operations,
                evidence,
                false,
                true,
                true,
                true);
    }

    private static void printFindings(List<Finding> findings) {
        if (findings.isEmpty()) {
            System.out.println("No governance findings.");
            return;
        }

        findings.forEach(finding -> System.out.printf(
                "[%s] %s: %s%n",
                finding.severity(),
                finding.code(),
                finding.message()));
    }

    public static void main(String[] args) {
        GovernancePolicy policy = new GovernancePolicy(
                true, true, true, true);

        ReleaseGovernanceService governance =
                new ReleaseGovernanceService(policy);
        ApiRelease release = buildRelease();

        System.out.println("API Contract Governance");
        System.out.println("Release: " + release.currentVersion);
        System.out.println("Previous: " + release.previousVersion);

        List<Finding> findings = governance.evaluate(release);
        printFindings(findings);
        System.out.println("Eligible: " + governance.isEligible(release));

        ObjectSchema requestSchema = createIncidentSchema();
        Map<String, Object> validPayload = new LinkedHashMap<>();
        validPayload.put("title", "Database connection failures");
        validPayload.put("severity", "high");
        validPayload.put("description", "Connection pool saturation");

        System.out.println("\nRequest schema validation:");
        printFindings(requestSchema.validate(validPayload));

        Map<String, Object> invalidPayload = new LinkedHashMap<>();
        invalidPayload.put("title", "X");
        invalidPayload.put("severity", "urgent");
        invalidPayload.put("internalRoutingKey", "unpublished");

        System.out.println("\nInvalid request:");
        printFindings(requestSchema.validate(invalidPayload));

        ReleaseWorkflow workflow = new ReleaseWorkflow();
        workflow.beginValidation();
        workflow.approve(findings);
        System.out.println("\nWorkflow state: " + workflow.state());

        // A workflow cannot be approved before validation has started.
        try {
            new ReleaseWorkflow().approve(findings);
        } catch (IllegalStateException exception) {
            System.out.println(
                    "Invalid transition rejected: " + exception.getMessage());
        }

        // The unused collection imports are intentionally avoided in the actual
        // release path; immutable records and defensive copies keep policy inputs
        // stable while the governance service evaluates them.
    }
}
