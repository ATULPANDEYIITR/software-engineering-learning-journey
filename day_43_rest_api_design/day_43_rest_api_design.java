import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/*
 * REST API DESIGN
 *
 * Enterprise-oriented domain model for:
 * URI resources
 * API versions
 * pagination policies
 * validation
 * compatibility and deprecation
 * mergeable policy decisions
 *
 * Compile:
 *   javac RestApiDesign.java
 *
 * Run:
 *   java RestApiDesign
 */

public class RestApiDesign {

    enum VersionState {
        ACTIVE,
        DEPRECATED,
        RETIRED
    }

    enum PaginationType {
        PAGE_NUMBER,
        CURSOR
    }

    record ApiVersion(
        String name,
        VersionState state,
        String sunsetDate
    ) {}

    record ResourceDefinition(
        String name,
        String collectionUri,
        String itemUriPattern,
        boolean paginated,
        PaginationType paginationType
    ) {}

    record PaginationPolicy(
        int defaultPageSize,
        int maximumPageSize,
        boolean allowPageNumber,
        boolean allowCursor
    ) {
        PaginationPolicy {
            if (defaultPageSize < 1) {
                throw new IllegalArgumentException(
                    "Default page size must be positive."
                );
            }

            if (maximumPageSize < defaultPageSize) {
                throw new IllegalArgumentException(
                    "Maximum page size cannot be smaller than default."
                );
            }
        }
    }

    record ApiRequest(
        String method,
        String path,
        Map<String, String> query
    ) {}

    record PolicyDecision(
        boolean accepted,
        int statusCode,
        String reason,
        List<String> warnings
    ) {
        static PolicyDecision accepted(
            String reason,
            List<String> warnings
        ) {
            return new PolicyDecision(
                true,
                200,
                reason,
                List.copyOf(warnings)
            );
        }

        static PolicyDecision rejected(
            int statusCode,
            String reason
        ) {
            return new PolicyDecision(
                false,
                statusCode,
                reason,
                List.of()
            );
        }
    }

    static final class ApiException extends RuntimeException {
        private final int statusCode;

        ApiException(int statusCode, String message) {
            super(message);
            this.statusCode = statusCode;
        }

        int statusCode() {
            return statusCode;
        }
    }

    static final class ApiRegistry {
        private final Map<String, ApiVersion> versions =
            new HashMap<>();

        private final Map<String, ResourceDefinition> resources =
            new HashMap<>();

        private final EnumMap<PaginationType, PaginationPolicy>
            paginationPolicies =
                new EnumMap<>(PaginationType.class);

        void registerVersion(ApiVersion version) {
            Objects.requireNonNull(version);
            versions.put(version.name(), version);
        }

        void registerResource(ResourceDefinition resource) {
            Objects.requireNonNull(resource);
            resources.put(resource.name(), resource);
        }

        void registerPaginationPolicy(
            PaginationType type,
            PaginationPolicy policy
        ) {
            paginationPolicies.put(type, policy);
        }

        Optional<ApiVersion> findVersion(String version) {
            return Optional.ofNullable(versions.get(version));
        }

        Optional<ResourceDefinition> findResourceByPath(
            String path
        ) {
            return resources.values()
                .stream()
                .filter(resource ->
                    path.equals(resource.collectionUri())
                    || path.startsWith(
                        resource.collectionUri() + "/"
                    ))
                .findFirst();
        }

        PaginationPolicy paginationPolicy(
            PaginationType type
        ) {
            PaginationPolicy policy =
                paginationPolicies.get(type);

            if (policy == null) {
                throw new ApiException(
                    500,
                    "No pagination policy has been configured."
                );
            }

            return policy;
        }
    }

    static final class UriParser {
        private static final Pattern VERSION_PATTERN =
            Pattern.compile("^/api/([^/]+)/(.+)$");

        static String extractVersion(String path) {
            Matcher matcher =
                VERSION_PATTERN.matcher(path);

            if (!matcher.matches()) {
                throw new ApiException(
                    400,
                    "URI must use the /api/{version}/{resource} form."
                );
            }

            return matcher.group(1);
        }

        static boolean isIndividualResource(
            ResourceDefinition resource,
            String path
        ) {
            String prefix = resource.collectionUri() + "/";

            if (!path.startsWith(prefix)) {
                return false;
            }

            String identifier =
                path.substring(prefix.length());

            return !identifier.isBlank()
                && !identifier.contains("/");
        }
    }

    static final class RequestValidator {
        private static final List<String> SAFE_METHODS =
            List.of("GET", "POST", "PUT", "PATCH", "DELETE");

        private final ApiRegistry registry;

        RequestValidator(ApiRegistry registry) {
            this.registry = registry;
        }

        PolicyDecision validate(ApiRequest request) {
            if (!SAFE_METHODS.contains(request.method())) {
                return PolicyDecision.rejected(
                    405,
                    "HTTP method is not supported by this API."
                );
            }

            String version;

            try {
                version = UriParser.extractVersion(
                    request.path()
                );
            } catch (ApiException error) {
                return PolicyDecision.rejected(
                    error.statusCode(),
                    error.getMessage()
                );
            }

            Optional<ApiVersion> versionResult =
                registry.findVersion(version);

            if (versionResult.isEmpty()) {
                return PolicyDecision.rejected(
                    404,
                    "The requested API version does not exist."
                );
            }

            ApiVersion apiVersion =
                versionResult.get();

            if (apiVersion.state() == VersionState.RETIRED) {
                return PolicyDecision.rejected(
                    410,
                    "The requested API version has been retired."
                );
            }

            Optional<ResourceDefinition> resourceResult =
                registry.findResourceByPath(
                    request.path()
                );

            if (resourceResult.isEmpty()) {
                return PolicyDecision.rejected(
                    404,
                    "The requested resource URI does not exist."
                );
            }

            ResourceDefinition resource =
                resourceResult.get();

            List<String> warnings =
                new ArrayList<>();

            if (
                apiVersion.state()
                    == VersionState.DEPRECATED
            ) {
                warnings.add(
                    "API version " + apiVersion.name()
                    + " is deprecated."
                );

                if (apiVersion.sunsetDate() != null) {
                    warnings.add(
                        "Sunset date: "
                        + apiVersion.sunsetDate()
                    );
                }
            }

            if (
                request.method().equals("GET")
                && resource.paginated()
            ) {
                try {
                    validatePagination(
                        request,
                        registry.paginationPolicy(
                            resource.paginationType()
                        )
                    );
                } catch (ApiException error) {
                    return PolicyDecision.rejected(
                        error.statusCode(),
                        error.getMessage()
                    );
                }
            }

            return PolicyDecision.accepted(
                "Request satisfies URI, version, resource, and pagination policies.",
                warnings
            );
        }

        private void validatePagination(
            ApiRequest request,
            PaginationPolicy policy
        ) {
            if (
                request.query().containsKey("page")
                && request.query().containsKey("cursor")
            ) {
                throw new ApiException(
                    400,
                    "Page-number and cursor pagination cannot be combined."
                );
            }

            if (request.query().containsKey("page")) {
                if (!policy.allowPageNumber()) {
                    throw new ApiException(
                        400,
                        "Page-number pagination is not supported."
                    );
                }

                validatePositiveInteger(
                    request.query().get("page"),
                    "page"
                );
            }

            if (request.query().containsKey("page_size")) {
                int pageSize =
                    validatePositiveInteger(
                        request.query().get("page_size"),
                        "page_size"
                    );

                if (pageSize > policy.maximumPageSize()) {
                    throw new ApiException(
                        400,
                        "page_size exceeds the configured API maximum."
                    );
                }
            }

            if (request.query().containsKey("cursor")
                && !policy.allowCursor()) {
                throw new ApiException(
                    400,
                    "Cursor pagination is not supported."
                );
            }
        }

        private int validatePositiveInteger(
            String value,
            String parameter
        ) {
            try {
                int parsed = Integer.parseInt(value);

                if (parsed < 1) {
                    throw new NumberFormatException();
                }

                return parsed;
            } catch (NumberFormatException error) {
                throw new ApiException(
                    400,
                    parameter
                        + " must be a positive integer."
                );
            }
        }
    }

    static void printDecision(
        ApiRequest request,
        PolicyDecision decision
    ) {
        System.out.println();
        System.out.println(
            request.method()
                + " "
                + request.path()
        );

        if (!request.query().isEmpty()) {
            System.out.println(
                "Query: " + request.query()
            );
        }

        System.out.println(
            "HTTP " + decision.statusCode()
        );
        System.out.println(
            decision.reason()
        );

        decision.warnings()
            .forEach(
                warning ->
                    System.out.println(
                        "Warning: " + warning
                    )
            );
    }

    public static void main(String[] args) {
        ApiRegistry registry =
            new ApiRegistry();

        registry.registerVersion(
            new ApiVersion(
                "v1",
                VersionState.ACTIVE,
                null
            )
        );

        registry.registerVersion(
            new ApiVersion(
                "v2",
                VersionState.DEPRECATED,
                "2027-06-30"
            )
        );

        registry.registerVersion(
            new ApiVersion(
                "v0",
                VersionState.RETIRED,
                "2026-01-31"
            )
        );

        registry.registerResource(
            new ResourceDefinition(
                "books",
                "/api/v1/books",
                "/api/v1/books/{id}",
                true,
                PaginationType.PAGE_NUMBER
            )
        );

        registry.registerResource(
            new ResourceDefinition(
                "orders",
                "/api/v1/orders",
                "/api/v1/orders/{id}",
                true,
                PaginationType.CURSOR
            )
        );

        registry.registerPaginationPolicy(
            PaginationType.PAGE_NUMBER,
            new PaginationPolicy(
                20,
                100,
                true,
                false
            )
        );

        registry.registerPaginationPolicy(
            PaginationType.CURSOR,
            new PaginationPolicy(
                50,
                100,
                false,
                true
            )
        );

        RequestValidator validator =
            new RequestValidator(registry);

        List<ApiRequest> requests =
            List.of(
                new ApiRequest(
                    "GET",
                    "/api/v1/books",
                    Map.of(
                        "page", "1",
                        "page_size", "20"
                    )
                ),
                new ApiRequest(
                    "GET",
                    "/api/v1/books/42",
                    Collections.emptyMap()
                ),
                new ApiRequest(
                    "GET",
                    "/api/v1/books",
                    Map.of(
                        "page", "0",
                        "page_size", "20"
                    )
                ),
                new ApiRequest(
                    "GET",
                    "/api/v1/books",
                    Map.of(
                        "page", "1",
                        "page_size", "500"
                    )
                ),
                new ApiRequest(
                    "GET",
                    "/api/v2/books",
                    Map.of(
                        "page", "1"
                    )
                ),
                new ApiRequest(
                    "GET",
                    "/api/v0/books",
                    Map.of(
                        "page", "1"
                    )
                ),
                new ApiRequest(
                    "GET",
                    "/api/v1/orders",
                    Map.of(
                        "cursor", "eyJpZCI6MTAw"
                    )
                ),
                new ApiRequest(
                    "GET",
                    "/api/v1/orders",
                    Map.of(
                        "page", "2",
                        "cursor", "abc"
                    )
                )
            );

        for (ApiRequest request : requests) {
            printDecision(
                request,
                validator.validate(request)
            );
        }

        System.out.println();
        System.out.println(
            "Evaluation timestamp: "
                + Instant.now()
        );
    }
}
