import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/*
 * DESIGN PATTERNS III
 * Repository, Facade, Decorator
 *
 * Enterprise scenario:
 * A compliance document platform manages controlled documents.
 *
 * Repository:
 *   Encapsulates persistence operations.
 *
 * Facade:
 *   Coordinates validation, persistence, approval, publication, and auditing.
 *
 * Decorator:
 *   Composes additional query policies without modifying the base query.
 */

public class DesignPatternsIII {

    // ========================================================
    // Domain model
    // ========================================================

    enum DocumentState {
        DRAFT,
        APPROVED,
        PUBLISHED,
        ARCHIVED
    }

    enum Permission {
        EDIT,
        APPROVE,
        PUBLISH
    }

    static final class Employee {
        private final String employeeId;
        private final String name;
        private final Set<Permission> permissions;

        Employee(
            String employeeId,
            String name,
            Set<Permission> permissions
        ) {
            this.employeeId = Objects.requireNonNull(employeeId);
            this.name = Objects.requireNonNull(name);
            this.permissions = EnumSet.copyOf(permissions);
        }

        boolean hasPermission(Permission permission) {
            return permissions.contains(permission);
        }

        String employeeId() {
            return employeeId;
        }

        String name() {
            return name;
        }
    }

    static final class Document {
        private final long id;
        private final String title;
        private final String ownerId;
        private DocumentState state;
        private final String content;

        Document(
            long id,
            String title,
            String ownerId,
            String content
        ) {
            if (id <= 0) {
                throw new IllegalArgumentException(
                    "Document ID must be positive."
                );
            }

            if (title == null || title.isBlank()) {
                throw new IllegalArgumentException(
                    "Document title is required."
                );
            }

            if (ownerId == null || ownerId.isBlank()) {
                throw new IllegalArgumentException(
                    "Document owner is required."
                );
            }

            if (content == null || content.isBlank()) {
                throw new IllegalArgumentException(
                    "Document content is required."
                );
            }

            this.id = id;
            this.title = title;
            this.ownerId = ownerId;
            this.content = content;
            this.state = DocumentState.DRAFT;
        }

        long id() {
            return id;
        }

        String title() {
            return title;
        }

        String ownerId() {
            return ownerId;
        }

        String content() {
            return content;
        }

        DocumentState state() {
            return state;
        }

        void approve() {
            if (state != DocumentState.DRAFT) {
                throw new IllegalStateException(
                    "Only draft documents can be approved."
                );
            }

            state = DocumentState.APPROVED;
        }

        void publish() {
            if (state != DocumentState.APPROVED) {
                throw new IllegalStateException(
                    "Only approved documents can be published."
                );
            }

            state = DocumentState.PUBLISHED;
        }

        void archive() {
            if (state != DocumentState.PUBLISHED) {
                throw new IllegalStateException(
                    "Only published documents can be archived."
                );
            }

            state = DocumentState.ARCHIVED;
        }

        @Override
        public String toString() {
            return "Document{" +
                "id=" + id +
                ", title='" + title + '\'' +
                ", ownerId='" + ownerId + '\'' +
                ", state=" + state +
                '}';
        }
    }

    // ========================================================
    // Repository
    // ========================================================

    interface DocumentRepository {
        Document save(Document document);

        Optional<Document> findById(long id);

        List<Document> findByOwner(String ownerId);

        List<Document> findAll();

        boolean delete(long id);
    }

    static final class InMemoryDocumentRepository
        implements DocumentRepository {

        private final Map<Long, Document> storage = new HashMap<>();

        @Override
        public Document save(Document document) {
            Objects.requireNonNull(document);
            storage.put(document.id(), document);
            return document;
        }

        @Override
        public Optional<Document> findById(long id) {
            return Optional.ofNullable(storage.get(id));
        }

        @Override
        public List<Document> findByOwner(String ownerId) {
            return storage.values()
                .stream()
                .filter(document -> document.ownerId().equals(ownerId))
                .sorted(Comparator.comparingLong(Document::id))
                .toList();
        }

        @Override
        public List<Document> findAll() {
            return new ArrayList<>(storage.values());
        }

        @Override
        public boolean delete(long id) {
            return storage.remove(id) != null;
        }
    }

    // ========================================================
    // Domain service
    // ========================================================

    static final class DocumentService {
        private final DocumentRepository repository;

        DocumentService(DocumentRepository repository) {
            this.repository = repository;
        }

        Document create(
            long id,
            String title,
            String ownerId,
            String content
        ) {
            if (repository.findById(id).isPresent()) {
                throw new IllegalStateException(
                    "A document with this ID already exists."
                );
            }

            return repository.save(
                new Document(id, title, ownerId, content)
            );
        }

        Document approve(Document document, Employee employee) {
            require(employee, Permission.APPROVE);
            document.approve();
            return repository.save(document);
        }

        Document publish(Document document, Employee employee) {
            require(employee, Permission.PUBLISH);
            document.publish();
            return repository.save(document);
        }

        private void require(
            Employee employee,
            Permission permission
        ) {
            if (!employee.hasPermission(permission)) {
                throw new SecurityException(
                    employee.name() +
                    " lacks permission " +
                    permission
                );
            }
        }
    }

    // ========================================================
    // Facade
    // ========================================================

    static final class ComplianceValidator {
        void validate(Document document) {
            if (document.content().length() < 30) {
                throw new IllegalStateException(
                    "Compliance publication requires substantive content."
                );
            }

            if (document.title().length() < 8) {
                throw new IllegalStateException(
                    "Compliance publication requires a descriptive title."
                );
            }
        }
    }

    static final class AuditService {
        void record(
            String action,
            Document document,
            Employee employee
        ) {
            System.out.println(
                "AUDIT action=" + action +
                " document=" + document.id() +
                " actor=" + employee.employeeId()
            );
        }
    }

    static final class SearchIndex {
        void index(Document document) {
            System.out.println(
                "INDEX document=" +
                document.id() +
                " state=" +
                document.state()
            );
        }
    }

    static final class PublicationFacade {
        private final DocumentRepository repository;
        private final DocumentService service;
        private final ComplianceValidator validator;
        private final AuditService audit;
        private final SearchIndex index;

        PublicationFacade(
            DocumentRepository repository,
            DocumentService service,
            ComplianceValidator validator,
            AuditService audit,
            SearchIndex index
        ) {
            this.repository = repository;
            this.service = service;
            this.validator = validator;
            this.audit = audit;
            this.index = index;
        }

        Document approveAndPublish(
            long documentId,
            Employee approver,
            Employee publisher
        ) {
            Document document = repository.findById(documentId)
                .orElseThrow(() ->
                    new IllegalArgumentException(
                        "Document does not exist."
                    )
                );

            validator.validate(document);

            Document approved =
                service.approve(document, approver);

            audit.record("APPROVE", approved, approver);

            Document published =
                service.publish(approved, publisher);

            index.index(published);
            audit.record("PUBLISH", published, publisher);

            return published;
        }
    }

    // ========================================================
    // Decorator
    // ========================================================

    interface DocumentQuery {
        List<Document> execute();
    }

    static final class RepositoryDocumentQuery
        implements DocumentQuery {

        private final DocumentRepository repository;

        RepositoryDocumentQuery(DocumentRepository repository) {
            this.repository = repository;
        }

        @Override
        public List<Document> execute() {
            return repository.findAll();
        }
    }

    abstract static class DocumentQueryDecorator
        implements DocumentQuery {

        protected final DocumentQuery wrapped;

        DocumentQueryDecorator(DocumentQuery wrapped) {
            this.wrapped = Objects.requireNonNull(wrapped);
        }
    }

    static final class PublishedOnlyDecorator
        extends DocumentQueryDecorator {

        PublishedOnlyDecorator(DocumentQuery wrapped) {
            super(wrapped);
        }

        @Override
        public List<Document> execute() {
            return wrapped.execute()
                .stream()
                .filter(
                    document ->
                        document.state() == DocumentState.PUBLISHED
                )
                .toList();
        }
    }

    static final class OwnerFilterDecorator
        extends DocumentQueryDecorator {

        private final String ownerId;

        OwnerFilterDecorator(
            DocumentQuery wrapped,
            String ownerId
        ) {
            super(wrapped);
            this.ownerId = ownerId;
        }

        @Override
        public List<Document> execute() {
            return wrapped.execute()
                .stream()
                .filter(
                    document ->
                        document.ownerId().equals(ownerId)
                )
                .toList();
        }
    }

    static final class TimingDecorator
        extends DocumentQueryDecorator {

        TimingDecorator(DocumentQuery wrapped) {
            super(wrapped);
        }

        @Override
        public List<Document> execute() {
            Instant start = Instant.now();

            try {
                return wrapped.execute();
            } finally {
                Duration elapsed =
                    Duration.between(start, Instant.now());

                System.out.println(
                    "QUERY duration_ms=" +
                    elapsed.toNanos() / 1_000_000.0
                );
            }
        }
    }

    static final class AuditDecorator
        extends DocumentQueryDecorator {

        AuditDecorator(DocumentQuery wrapped) {
            super(wrapped);
        }

        @Override
        public List<Document> execute() {
            System.out.println("AUDIT document query started.");

            List<Document> result = wrapped.execute();

            System.out.println(
                "AUDIT document query returned " +
                result.size() +
                " record(s)."
            );

            return result;
        }
    }

    // ========================================================
    // Demonstration
    // ========================================================

    public static void main(String[] args) {
        DocumentRepository repository =
            new InMemoryDocumentRepository();

        DocumentService service =
            new DocumentService(repository);

        Employee reviewer = new Employee(
            "EMP-REVIEWER",
            "Riya",
            EnumSet.of(
                Permission.EDIT,
                Permission.APPROVE
            )
        );

        Employee publisher = new Employee(
            "EMP-PUBLISHER",
            "Arun",
            EnumSet.of(
                Permission.PUBLISH
            )
        );

        service.create(
            1001,
            "Information Security Policy",
            "EMP-AUTHOR",
            "This policy defines controlled handling of sensitive enterprise information."
        );

        service.create(
            1002,
            "Internal Draft",
            "EMP-AUTHOR",
            "Draft material awaiting formal approval."
        );

        ComplianceValidator validator =
            new ComplianceValidator();

        AuditService audit =
            new AuditService();

        SearchIndex index =
            new SearchIndex();

        PublicationFacade facade =
            new PublicationFacade(
                repository,
                service,
                validator,
                audit,
                index
            );

        System.out.println("Facade workflow:");

        facade.approveAndPublish(
            1001,
            reviewer,
            publisher
        );

        System.out.println("\nDecorator pipeline:");

        DocumentQuery query =
            new RepositoryDocumentQuery(repository);

        query =
            new OwnerFilterDecorator(
                query,
                "EMP-AUTHOR"
            );

        query =
            new PublishedOnlyDecorator(query);

        query =
            new AuditDecorator(query);

        query =
            new TimingDecorator(query);

        query.execute()
            .forEach(System.out::println);

        System.out.println("\nInvalid transition:");

        try {
            Document draft =
                repository.findById(1002)
                    .orElseThrow();

            service.publish(draft, publisher);
        } catch (Exception exception) {
            System.out.println(
                "Expected failure: " +
                exception.getMessage()
            );
        }

        System.out.println("\nPermission enforcement:");

        Employee unauthorized =
            new Employee(
                "EMP-READONLY",
                "Neha",
                EnumSet.noneOf(Permission.class)
            );

        try {
            Document draft =
                repository.findById(1002)
                    .orElseThrow();

            service.approve(draft, unauthorized);
        } catch (Exception exception) {
            System.out.println(
                "Expected security failure: " +
                exception.getMessage()
            );
        }
    }
}
