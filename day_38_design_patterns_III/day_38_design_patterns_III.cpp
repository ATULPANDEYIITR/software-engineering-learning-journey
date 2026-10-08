#include <algorithm>
#include <chrono>
#include <functional>
#include <iomanip>
#include <iostream>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * DESIGN PATTERNS III
 *
 * Technical case study:
 * A digital document platform needs to store documents, expose a simple
 * publishing workflow, and add operational behavior such as auditing,
 * compression metadata, and timing without changing the core document logic.
 *
 * Repository:
 *   Separates document persistence from domain services.
 *
 * Facade:
 *   Coordinates validation, repository access, publication, and audit steps.
 *
 * Decorator:
 *   Wraps the document service and adds behavior dynamically.
 */

struct Document {
    int id;
    std::string title;
    std::string owner;
    std::string body;
    bool published{false};
};

class DocumentRepository {
public:
    virtual ~DocumentRepository() = default;

    virtual void save(const Document& document) = 0;
    virtual std::optional<Document> findById(int id) const = 0;
    virtual std::vector<Document> findByOwner(
        const std::string& owner) const = 0;
    virtual bool remove(int id) = 0;
};

class InMemoryDocumentRepository final : public DocumentRepository {
private:
    std::unordered_map<int, Document> documents;

public:
    void save(const Document& document) override {
        if (document.id <= 0) {
            throw std::invalid_argument("Document ID must be positive.");
        }

        if (document.title.empty()) {
            throw std::invalid_argument("Document title cannot be empty.");
        }

        documents[document.id] = document;
    }

    std::optional<Document> findById(int id) const override {
        auto iterator = documents.find(id);

        if (iterator == documents.end()) {
            return std::nullopt;
        }

        return iterator->second;
    }

    std::vector<Document> findByOwner(
        const std::string& owner) const override {

        std::vector<Document> result;

        for (const auto& [id, document] : documents) {
            if (document.owner == owner) {
                result.push_back(document);
            }
        }

        std::sort(
            result.begin(),
            result.end(),
            [](const Document& left, const Document& right) {
                return left.id < right.id;
            }
        );

        return result;
    }

    bool remove(int id) override {
        return documents.erase(id) > 0;
    }
};

class DocumentService {
private:
    DocumentRepository& repository;

public:
    explicit DocumentService(DocumentRepository& repository)
        : repository(repository) {}

    Document create(
        int id,
        const std::string& title,
        const std::string& owner,
        const std::string& body) {

        if (repository.findById(id).has_value()) {
            throw std::runtime_error("Document already exists.");
        }

        if (owner.empty()) {
            throw std::invalid_argument("Owner is required.");
        }

        if (body.empty()) {
            throw std::invalid_argument("Document body is required.");
        }

        Document document{
            id,
            title,
            owner,
            body,
            false
        };

        repository.save(document);
        return document;
    }

    Document publish(int id) {
        auto document = repository.findById(id);

        if (!document.has_value()) {
            throw std::runtime_error("Cannot publish a missing document.");
        }

        if (document->published) {
            throw std::runtime_error("Document is already published.");
        }

        document->published = true;
        repository.save(*document);

        return *document;
    }
};

// ============================================================
// Facade
// ============================================================

class ContentValidator {
public:
    void validateForPublication(const Document& document) const {
        if (document.title.size() < 5) {
            throw std::runtime_error(
                "Publication requires a title of at least five characters."
            );
        }

        if (document.body.size() < 20) {
            throw std::runtime_error(
                "Publication requires meaningful document content."
            );
        }

        if (document.owner.empty()) {
            throw std::runtime_error(
                "Publication requires an identified owner."
            );
        }
    }
};

class PublicationIndex {
public:
    void index(const Document& document) {
        std::cout
            << "Indexed document "
            << document.id
            << " for publication search.\n";
    }
};

class AuditTrail {
public:
    void record(const Document& document, const std::string& action) {
        std::cout
            << "AUDIT action="
            << action
            << " document="
            << document.id
            << " owner="
            << document.owner
            << '\n';
    }
};

class PublicationFacade {
private:
    DocumentService& documentService;
    const ContentValidator& validator;
    PublicationIndex& index;
    AuditTrail& audit;

public:
    PublicationFacade(
        DocumentService& documentService,
        const ContentValidator& validator,
        PublicationIndex& index,
        AuditTrail& audit
    )
        : documentService(documentService),
          validator(validator),
          index(index),
          audit(audit) {}

    Document publishDocument(int id) {
        auto document = documentService.repository.findById(id);

        if (!document.has_value()) {
            throw std::runtime_error("Document does not exist.");
        }

        validator.validateForPublication(*document);

        Document published = documentService.publish(id);

        index.index(published);
        audit.record(published, "PUBLISH");

        return published;
    }
};

/*
 * The facade above should not expose the repository internals directly.
 * A production implementation would keep the repository reference private
 * inside DocumentService and provide a dedicated read operation. This version
 * therefore uses a specialized service facade below to maintain encapsulation.
 */

class PublicationWorkflow {
private:
    DocumentRepository& repository;
    DocumentService& documentService;
    const ContentValidator& validator;
    PublicationIndex& index;
    AuditTrail& audit;

public:
    PublicationWorkflow(
        DocumentRepository& repository,
        DocumentService& documentService,
        const ContentValidator& validator,
        PublicationIndex& index,
        AuditTrail& audit
    )
        : repository(repository),
          documentService(documentService),
          validator(validator),
          index(index),
          audit(audit) {}

    Document publish(int id) {
        auto document = repository.findById(id);

        if (!document.has_value()) {
            throw std::runtime_error("Document does not exist.");
        }

        validator.validateForPublication(*document);

        Document result = documentService.publish(id);

        index.index(result);
        audit.record(result, "PUBLISH");

        return result;
    }
};

// ============================================================
// Decorator
// ============================================================

class DocumentQuery {
public:
    virtual ~DocumentQuery() = default;

    virtual std::vector<Document> execute(
        const std::string& owner) const = 0;
};

class RepositoryDocumentQuery final : public DocumentQuery {
private:
    const DocumentRepository& repository;

public:
    explicit RepositoryDocumentQuery(
        const DocumentRepository& repository
    )
        : repository(repository) {}

    std::vector<Document> execute(
        const std::string& owner) const override {

        return repository.findByOwner(owner);
    }
};

class DocumentQueryDecorator : public DocumentQuery {
protected:
    std::unique_ptr<DocumentQuery> wrapped;

public:
    explicit DocumentQueryDecorator(
        std::unique_ptr<DocumentQuery> wrapped
    )
        : wrapped(std::move(wrapped)) {}
};

class PublishedOnlyDecorator final : public DocumentQueryDecorator {
public:
    using DocumentQueryDecorator::DocumentQueryDecorator;

    std::vector<Document> execute(
        const std::string& owner) const override {

        auto documents = wrapped->execute(owner);

        documents.erase(
            std::remove_if(
                documents.begin(),
                documents.end(),
                [](const Document& document) {
                    return !document.published;
                }
            ),
            documents.end()
        );

        return documents;
    }
};

class AuditQueryDecorator final : public DocumentQueryDecorator {
public:
    using DocumentQueryDecorator::DocumentQueryDecorator;

    std::vector<Document> execute(
        const std::string& owner) const override {

        std::cout
            << "AUDIT query owner="
            << owner
            << '\n';

        auto documents = wrapped->execute(owner);

        std::cout
            << "AUDIT result_count="
            << documents.size()
            << '\n';

        return documents;
    }
};

class TimingQueryDecorator final : public DocumentQueryDecorator {
public:
    using DocumentQueryDecorator::DocumentQueryDecorator;

    std::vector<Document> execute(
        const std::string& owner) const override {

        const auto start = std::chrono::steady_clock::now();

        auto result = wrapped->execute(owner);

        const auto finish = std::chrono::steady_clock::now();

        const auto elapsed =
            std::chrono::duration<double, std::milli>(
                finish - start
            ).count();

        std::cout
            << std::fixed
            << std::setprecision(3)
            << "QUERY duration_ms="
            << elapsed
            << '\n';

        return result;
    }
};

// ============================================================
// Demonstration
// ============================================================

void printDocuments(const std::vector<Document>& documents) {
    for (const auto& document : documents) {
        std::cout
            << "Document "
            << document.id
            << " | "
            << document.title
            << " | published="
            << std::boolalpha
            << document.published
            << '\n';
    }
}

int main() {
    try {
        InMemoryDocumentRepository repository;
        DocumentService documentService(repository);

        documentService.create(
            1,
            "Repository Architecture",
            "alice",
            "This document explains persistence boundaries."
        );

        documentService.create(
            2,
            "Decorator Operations",
            "alice",
            "This document explains dynamic service behavior."
        );

        documentService.create(
            3,
            "Draft Notes",
            "bob",
            "Short draft."
        );

        ContentValidator validator;
        PublicationIndex index;
        AuditTrail audit;

        PublicationWorkflow workflow(
            repository,
            documentService,
            validator,
            index,
            audit
        );

        std::cout << "Facade publication workflow:\n";

        workflow.publish(1);
        workflow.publish(2);

        std::cout << "\nDecorated query:\n";

        std::unique_ptr<DocumentQuery> query =
            std::make_unique<RepositoryDocumentQuery>(repository);

        query =
            std::make_unique<PublishedOnlyDecorator>(
                std::move(query)
            );

        query =
            std::make_unique<AuditQueryDecorator>(
                std::move(query)
            );

        query =
            std::make_unique<TimingQueryDecorator>(
                std::move(query)
            );

        const auto publishedDocuments = query->execute("alice");
        printDocuments(publishedDocuments);

        std::cout << "\nFailure handling:\n";

        try {
            workflow.publish(3);
        } catch (const std::exception& error) {
            std::cout
                << "Expected validation failure: "
                << error.what()
                << '\n';
        }

        try {
            documentService.create(
                1,
                "Duplicate",
                "alice",
                "Duplicate document body."
            );
        } catch (const std::exception& error) {
            std::cout
                << "Expected repository failure: "
                << error.what()
                << '\n';
        }

        std::cout << "\nRepository boundary demonstration:\n";

        const auto aliceDocuments = repository.findByOwner("alice");
        printDocuments(aliceDocuments);

    } catch (const std::exception& error) {
        std::cerr
            << "Application error: "
            << error.what()
            << '\n';

        return 1;
    }

    return 0;
}
