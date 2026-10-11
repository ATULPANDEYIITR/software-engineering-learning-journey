import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;

/*
 * API Fundamentals: REST, Resources, Endpoints, and HTTP
 *
 * Enterprise-oriented repository model for an API platform. The design keeps
 * HTTP concerns at the API boundary and domain rules in explicit services.
 */
public class ApiFundamentals {

    enum HttpMethod {
        GET, POST, PUT, PATCH, DELETE, HEAD
    }

    enum ResourceStatus {
        ACTIVE, INACTIVE, MAINTENANCE
    }

    enum HttpStatus {
        OK(200),
        CREATED(201),
        NO_CONTENT(204),
        NOT_MODIFIED(304),
        BAD_REQUEST(400),
        NOT_FOUND(404),
        METHOD_NOT_ALLOWED(405),
        UNPROCESSABLE_ENTITY(422);

        private final int code;

        HttpStatus(int code) {
            this.code = code;
        }

        public int code() {
            return code;
        }
    }

    record Resource(
        int id,
        String name,
        String category,
        ResourceStatus status,
        int version,
        Instant createdAt,
        Instant updatedAt
    ) {
        Resource {
            Objects.requireNonNull(name);
            Objects.requireNonNull(category);
            Objects.requireNonNull(status);
            Objects.requireNonNull(createdAt);
            Objects.requireNonNull(updatedAt);
        }

        Resource replace(
            String newName,
            String newCategory,
            ResourceStatus newStatus
        ) {
            return new Resource(
                id,
                newName,
                newCategory,
                newStatus,
                version + 1,
                createdAt,
                Instant.now()
            );
        }
    }

    record ApiResponse(
        HttpStatus status,
        Map<String, String> headers,
        Object body
    ) {
        ApiResponse {
            headers = Map.copyOf(headers);
        }

        static ApiResponse json(
            HttpStatus status,
            Object body
        ) {
            return new ApiResponse(
                status,
                Map.of("Content-Type", "application/json"),
                body
            );
        }
    }

    static class ApiException extends RuntimeException {
        private final HttpStatus status;

        ApiException(HttpStatus status, String message) {
            super(message);
            this.status = status;
        }

        HttpStatus status() {
            return status;
        }
    }

    interface ResourceRepository {
        Resource save(Resource resource);

        Optional<Resource> findById(int id);

        List<Resource> findAll();

        void deleteById(int id);
    }

    static final class InMemoryResourceRepository
        implements ResourceRepository {

        private final Map<Integer, Resource> storage = new HashMap<>();

        @Override
        public synchronized Resource save(Resource resource) {
            storage.put(resource.id(), resource);
            return resource;
        }

        @Override
        public synchronized Optional<Resource> findById(int id) {
            return Optional.ofNullable(storage.get(id));
        }

        @Override
        public synchronized List<Resource> findAll() {
            return new ArrayList<>(storage.values());
        }

        @Override
        public synchronized void deleteById(int id) {
            storage.remove(id);
        }
    }

    static final class ResourceValidator {
        private static final Set<ResourceStatus> ALLOWED_STATUSES =
            EnumSet.allOf(ResourceStatus.class);

        static void validate(
            String name,
            String category,
            ResourceStatus status
        ) {
            if (name == null || name.isBlank()) {
                throw new ApiException(
                    HttpStatus.UNPROCESSABLE_ENTITY,
                    "Resource name is required"
                );
            }

            if (name.length() > 100) {
                throw new ApiException(
                    HttpStatus.UNPROCESSABLE_ENTITY,
                    "Resource name is too long"
                );
            }

            if (category == null || category.isBlank()) {
                throw new ApiException(
                    HttpStatus.UNPROCESSABLE_ENTITY,
                    "Resource category is required"
                );
            }

            if (!ALLOWED_STATUSES.contains(status)) {
                throw new ApiException(
                    HttpStatus.UNPROCESSABLE_ENTITY,
                    "Unsupported resource status"
                );
            }
        }

        private ResourceValidator() {}
    }

    static final class ResourceService {
        private final ResourceRepository repository;
        private final AtomicInteger sequence = new AtomicInteger(1);

        ResourceService(ResourceRepository repository) {
            this.repository = repository;
        }

        Resource create(
            String name,
            String category,
            ResourceStatus status
        ) {
            ResourceValidator.validate(name, category, status);

            Instant now = Instant.now();

            Resource resource = new Resource(
                sequence.getAndIncrement(),
                name.trim(),
                category.trim(),
                status,
                1,
                now,
                now
            );

            return repository.save(resource);
        }

        Resource get(int id) {
            return repository.findById(id).orElseThrow(
                () -> new ApiException(
                    HttpStatus.NOT_FOUND,
                    "Resource " + id + " was not found"
                )
            );
        }

        Resource replace(
            int id,
            String name,
            String category,
            ResourceStatus status
        ) {
            Resource current = get(id);

            ResourceValidator.validate(name, category, status);

            return repository.save(
                current.replace(
                    name.trim(),
                    category.trim(),
                    status
                )
            );
        }

        Resource changeStatus(
            int id,
            ResourceStatus status
        ) {
            Resource current = get(id);

            ResourceValidator.validate(
                current.name(),
                current.category(),
                status
            );

            return repository.save(
                current.replace(
                    current.name(),
                    current.category(),
                    status
                )
            );
        }

        void delete(int id) {
            get(id);
            repository.deleteById(id);
        }

        List<Resource> searchByCategory(String category) {
            return repository.findAll()
                .stream()
                .filter(resource ->
                    resource.category().equalsIgnoreCase(category)
                )
                .sorted((a, b) ->
                    Integer.compare(a.id(), b.id())
                )
                .toList();
        }
    }

    static final class HttpRepresentationService {

        static String etag(Resource resource) {
            return "\"resource-" +
                resource.id() +
                "-version-" +
                resource.version() +
                "\"";
        }

        static Map<String, Object> representation(
            Resource resource
        ) {
            return Map.of(
                "id", resource.id(),
                "name", resource.name(),
                "category", resource.category(),
                "status", resource.status().name().toLowerCase(),
                "version", resource.version(),
                "createdAt", resource.createdAt().toString(),
                "updatedAt", resource.updatedAt().toString()
            );
        }
    }

    static final class RestEndpointService {
        private final ResourceService resources;

        RestEndpointService(ResourceService resources) {
            this.resources = resources;
        }

        ApiResponse dispatch(
            HttpMethod method,
            String path,
            Map<String, String> headers
        ) {
            try {
                if (path.equals("/api/v1/resources")) {
                    return collection(method);
                }

                if (path.matches("/api/v1/resources/[0-9]+")) {
                    int id = Integer.parseInt(
                        path.substring(path.lastIndexOf('/') + 1)
                    );

                    return member(method, id, headers);
                }

                throw new ApiException(
                    HttpStatus.NOT_FOUND,
                    "Endpoint does not exist"
                );
            } catch (ApiException exception) {
                return ApiResponse.json(
                    exception.status(),
                    Map.of("error", exception.getMessage())
                );
            }
        }

        private ApiResponse collection(HttpMethod method) {
            if (method == HttpMethod.GET) {
                return ApiResponse.json(
                    HttpStatus.OK,
                    resources.searchByCategory("application")
                );
            }

            if (method == HttpMethod.POST) {
                Resource created = resources.create(
                    "Enterprise Order API",
                    "application",
                    ResourceStatus.ACTIVE
                );

                return new ApiResponse(
                    HttpStatus.CREATED,
                    Map.of(
                        "Location",
                        "/api/v1/resources/" + created.id(),
                        "ETag",
                        HttpRepresentationService.etag(created)
                    ),
                    HttpRepresentationService.representation(created)
                );
            }

            throw new ApiException(
                HttpStatus.METHOD_NOT_ALLOWED,
                "Method is not allowed on the collection"
            );
        }

        private ApiResponse member(
            HttpMethod method,
            int id,
            Map<String, String> headers
        ) {
            Resource resource = resources.get(id);
            String etag = HttpRepresentationService.etag(resource);

            if (method == HttpMethod.GET) {
                String supplied = headers.get("If-None-Match");

                if (etag.equals(supplied)) {
                    return new ApiResponse(
                        HttpStatus.NOT_MODIFIED,
                        Map.of("ETag", etag),
                        null
                    );
                }

                return new ApiResponse(
                    HttpStatus.OK,
                    Map.of("ETag", etag),
                    HttpRepresentationService.representation(resource)
                );
            }

            if (method == HttpMethod.HEAD) {
                return new ApiResponse(
                    HttpStatus.OK,
                    Map.of("ETag", etag),
                    null
                );
            }

            if (method == HttpMethod.PATCH) {
                Resource updated =
                    resources.changeStatus(id, ResourceStatus.MAINTENANCE);

                return new ApiResponse(
                    HttpStatus.OK,
                    Map.of(
                        "ETag",
                        HttpRepresentationService.etag(updated)
                    ),
                    HttpRepresentationService.representation(updated)
                );
            }

            if (method == HttpMethod.DELETE) {
                resources.delete(id);

                return new ApiResponse(
                    HttpStatus.NO_CONTENT,
                    Map.of(),
                    null
                );
            }

            throw new ApiException(
                HttpStatus.METHOD_NOT_ALLOWED,
                "Method is not allowed on the member endpoint"
            );
        }
    }

    static void printResponse(
        String operation,
        ApiResponse response
    ) {
        System.out.println("\n" + operation);
        System.out.println(
            "HTTP " + response.status().code()
        );

        response.headers().forEach(
            (key, value) ->
                System.out.println(key + ": " + value)
        );

        if (response.body() != null) {
            System.out.println(response.body());
        }
    }

    public static void main(String[] args) {
        ResourceRepository repository =
            new InMemoryResourceRepository();

        ResourceService service =
            new ResourceService(repository);

        service.create(
            "Identity API",
            "security",
            ResourceStatus.ACTIVE
        );

        service.create(
            "Order API",
            "application",
            ResourceStatus.ACTIVE
        );

        service.create(
            "Reporting API",
            "data",
            ResourceStatus.MAINTENANCE
        );

        RestEndpointService api =
            new RestEndpointService(service);

        ApiResponse collection =
            api.dispatch(
                HttpMethod.GET,
                "/api/v1/resources",
                Map.of("Accept", "application/json")
            );

        printResponse(
            "Collection resource retrieval",
            collection
        );

        ApiResponse created =
            api.dispatch(
                HttpMethod.POST,
                "/api/v1/resources",
                Map.of("Content-Type", "application/json")
            );

        printResponse(
            "Resource creation",
            created
        );

        ApiResponse member =
            api.dispatch(
                HttpMethod.GET,
                "/api/v1/resources/2",
                Map.of("Accept", "application/json")
            );

        printResponse(
            "Member resource retrieval",
            member
        );

        String etag = member.headers().get("ETag");

        ApiResponse cached =
            api.dispatch(
                HttpMethod.GET,
                "/api/v1/resources/2",
                Map.of(
                    "Accept", "application/json",
                    "If-None-Match", etag
                )
            );

        printResponse(
            "Conditional HTTP retrieval",
            cached
        );

        ApiResponse patched =
            api.dispatch(
                HttpMethod.PATCH,
                "/api/v1/resources/2",
                Map.of("Content-Type", "application/json")
            );

        printResponse(
            "Partial resource update",
            patched
        );

        ApiResponse deleted =
            api.dispatch(
                HttpMethod.DELETE,
                "/api/v1/resources/3",
                Map.of()
            );

        printResponse(
            "Resource deletion",
            deleted
        );
    }
}
