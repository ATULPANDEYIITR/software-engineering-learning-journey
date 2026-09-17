#include <algorithm>
#include <chrono>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
    Object-Oriented Programming in C++17
    ====================================

    Industry-style case study:
    Library Management System

    The program demonstrates:
    - Classes and objects
    - Constructors
    - Attributes and methods
    - Encapsulation
    - Access control
    - const correctness
    - static members
    - inheritance
    - virtual functions
    - overriding
    - runtime polymorphism
    - abstract classes
    - interfaces
    - composition
    - aggregation
    - RAII
    - smart pointers
    - operator overloading
    - exceptions
    - templates
    - STL containers
    - algorithms
    - dependency injection
    - strategy pattern
    - factory pattern
    - validation
    - performance considerations
    - edge cases

    Compile:
        g++ -std=c++17 -Wall -Wextra -pedantic main.cpp -o oop_case_study

    Run:
        ./oop_case_study
*/

namespace oop_demo {

// =============================================================================
// Utility
// =============================================================================

void printSection(const std::string& title) {
    std::cout << "\n" << std::string(78, '=') << "\n";
    std::cout << title << "\n";
    std::cout << std::string(78, '=') << "\n";
}

// =============================================================================
// 1. BASIC CLASS
// =============================================================================

class Student {
private:
    std::string name_;
    int age_;

public:
    Student(std::string name, int age)
        : name_(std::move(name)), age_(age) {
        if (name_.empty()) {
            throw std::invalid_argument("Student name cannot be empty.");
        }

        if (age_ <= 0) {
            throw std::invalid_argument("Student age must be positive.");
        }
    }

    const std::string& name() const {
        return name_;
    }

    int age() const {
        return age_;
    }

    std::string introduce() const {
        return "My name is " + name_ +
               " and I am " + std::to_string(age_) +
               " years old.";
    }
};

// =============================================================================
// 2. ENCAPSULATION
// =============================================================================

class BankAccount {
private:
    std::string owner_;
    double balance_;
    std::size_t transactionCount_;

public:
    explicit BankAccount(
        std::string owner,
        double openingBalance = 0.0
    )
        : owner_(std::move(owner)),
          balance_(openingBalance),
          transactionCount_(0) {

        if (owner_.empty()) {
            throw std::invalid_argument("Owner cannot be empty.");
        }

        if (!std::isfinite(balance_) || balance_ < 0.0) {
            throw std::invalid_argument(
                "Opening balance must be finite and non-negative."
            );
        }
    }

    void deposit(double amount) {
        if (!std::isfinite(amount) || amount <= 0.0) {
            throw std::invalid_argument(
                "Deposit must be positive and finite."
            );
        }

        balance_ += amount;
        ++transactionCount_;
    }

    void withdraw(double amount) {
        if (!std::isfinite(amount) || amount <= 0.0) {
            throw std::invalid_argument(
                "Withdrawal must be positive and finite."
            );
        }

        if (amount > balance_) {
            throw std::runtime_error("Insufficient funds.");
        }

        balance_ -= amount;
        ++transactionCount_;
    }

    double balance() const {
        return balance_;
    }

    std::size_t transactionCount() const {
        return transactionCount_;
    }
};

// =============================================================================
// 3. INHERITANCE AND POLYMORPHISM
// =============================================================================

class Vehicle {
protected:
    std::string brand_;

public:
    explicit Vehicle(std::string brand)
        : brand_(std::move(brand)) {}

    virtual ~Vehicle() = default;

    virtual std::string move() const {
        return brand_ + " vehicle is moving.";
    }
};

class Car : public Vehicle {
public:
    explicit Car(std::string brand)
        : Vehicle(std::move(brand)) {}

    std::string move() const override {
        return brand_ + " car is driving.";
    }
};

class ElectricCar : public Car {
private:
    double batteryKWh_;

public:
    ElectricCar(
        std::string brand,
        double batteryKWh
    )
        : Car(std::move(brand)),
          batteryKWh_(batteryKWh) {

        if (!std::isfinite(batteryKWh_) ||
            batteryKWh_ <= 0.0) {
            throw std::invalid_argument(
                "Battery capacity must be positive."
            );
        }
    }

    std::string move() const override {
        return brand_ +
               " electric car is driving silently.";
    }

    double batteryKWh() const {
        return batteryKWh_;
    }
};

// =============================================================================
// 4. ABSTRACT CLASS
// =============================================================================

class Shape {
public:
    virtual ~Shape() = default;

    virtual double area() const = 0;
    virtual double perimeter() const = 0;
};

class Rectangle : public Shape {
private:
    double width_;
    double height_;

public:
    Rectangle(double width, double height)
        : width_(width), height_(height) {

        if (width_ <= 0.0 || height_ <= 0.0) {
            throw std::invalid_argument(
                "Rectangle dimensions must be positive."
            );
        }
    }

    double area() const override {
        return width_ * height_;
    }

    double perimeter() const override {
        return 2.0 * (width_ + height_);
    }
};

class Circle : public Shape {
private:
    double radius_;

public:
    explicit Circle(double radius)
        : radius_(radius) {

        if (radius_ <= 0.0) {
            throw std::invalid_argument(
                "Circle radius must be positive."
            );
        }
    }

    double area() const override {
        return std::acos(-1.0) * radius_ * radius_;
    }

    double perimeter() const override {
        return 2.0 * std::acos(-1.0) * radius_;
    }
};

// =============================================================================
// 5. COMPOSITION
// =============================================================================

class Engine {
private:
    bool running_;

public:
    Engine()
        : running_(false) {}

    void start() {
        running_ = true;
    }

    void stop() {
        running_ = false;
    }

    bool isRunning() const {
        return running_;
    }
};

class ComposedCar {
private:
    std::string brand_;
    Engine engine_;

public:
    explicit ComposedCar(std::string brand)
        : brand_(std::move(brand)) {}

    void start() {
        engine_.start();
    }

    void stop() {
        engine_.stop();
    }

    bool isRunning() const {
        return engine_.isRunning();
    }

    const std::string& brand() const {
        return brand_;
    }
};

// =============================================================================
// 6. OPERATOR OVERLOADING
// =============================================================================

class Money {
private:
    long long cents_;

public:
    explicit Money(long long cents = 0)
        : cents_(cents) {}

    long long cents() const {
        return cents_;
    }

    Money operator+(const Money& other) const {
        return Money(cents_ + other.cents_);
    }

    Money operator-(const Money& other) const {
        return Money(cents_ - other.cents_);
    }

    bool operator==(const Money& other) const {
        return cents_ == other.cents_;
    }

    bool operator<(const Money& other) const {
        return cents_ < other.cents_;
    }
};

std::ostream& operator<<(
    std::ostream& output,
    const Money& money
) {
    output << "$"
           << money.cents() / 100
           << "."
           << std::setw(2)
           << std::setfill('0')
           << std::llabs(money.cents() % 100)
           << std::setfill(' ');

    return output;
}

// =============================================================================
// 7. DOMAIN OBJECT: BOOK
// =============================================================================

class Book {
private:
    std::string isbn_;
    std::string title_;
    std::string author_;

public:
    Book(
        std::string isbn,
        std::string title,
        std::string author
    )
        : isbn_(std::move(isbn)),
          title_(std::move(title)),
          author_(std::move(author)) {

        if (isbn_.empty()) {
            throw std::invalid_argument(
                "ISBN cannot be empty."
            );
        }

        if (title_.empty()) {
            throw std::invalid_argument(
                "Title cannot be empty."
            );
        }

        if (author_.empty()) {
            throw std::invalid_argument(
                "Author cannot be empty."
            );
        }
    }

    const std::string& isbn() const {
        return isbn_;
    }

    const std::string& title() const {
        return title_;
    }

    const std::string& author() const {
        return author_;
    }
};

// =============================================================================
// 8. DOMAIN OBJECT: MEMBER
// =============================================================================

class LibraryMember {
private:
    std::string memberId_;
    std::string name_;
    std::set<std::string> borrowedIsbns_;

public:
    LibraryMember(
        std::string memberId,
        std::string name
    )
        : memberId_(std::move(memberId)),
          name_(std::move(name)) {

        if (memberId_.empty()) {
            throw std::invalid_argument(
                "Member ID cannot be empty."
            );
        }

        if (name_.empty()) {
            throw std::invalid_argument(
                "Member name cannot be empty."
            );
        }
    }

    const std::string& memberId() const {
        return memberId_;
    }

    const std::string& name() const {
        return name_;
    }

    bool hasBorrowed(const std::string& isbn) const {
        return borrowedIsbns_.find(isbn) !=
               borrowedIsbns_.end();
    }

    void borrow(const std::string& isbn) {
        borrowedIsbns_.insert(isbn);
    }

    void returnBook(const std::string& isbn) {
        borrowedIsbns_.erase(isbn);
    }

    std::size_t borrowedCount() const {
        return borrowedIsbns_.size();
    }
};

// =============================================================================
// 9. NOTIFICATION INTERFACE
// =============================================================================

class Notifier {
public:
    virtual ~Notifier() = default;

    virtual void send(
        const std::string& message
    ) = 0;
};

class ConsoleNotifier : public Notifier {
public:
    void send(
        const std::string& message
    ) override {
        std::cout << "[NOTIFICATION] "
                  << message
                  << "\n";
    }
};

// =============================================================================
// 10. LIBRARY MANAGEMENT SYSTEM
// =============================================================================

class Library {
private:
    std::unordered_map<
        std::string,
        Book
    > books_;

    std::unordered_map<
        std::string,
        LibraryMember
    > members_;

    std::shared_ptr<Notifier> notifier_;

    static constexpr std::size_t
        MAX_BOOKS_PER_MEMBER = 3;

    bool isBookBorrowed(
        const std::string& isbn
    ) const {

        for (const auto& entry : members_) {
            if (entry.second.hasBorrowed(isbn)) {
                return true;
            }
        }

        return false;
    }

    Book& getBook(const std::string& isbn) {
        auto iterator = books_.find(isbn);

        if (iterator == books_.end()) {
            throw std::out_of_range(
                "Unknown ISBN: " + isbn
            );
        }

        return iterator->second;
    }

    LibraryMember& getMember(
        const std::string& memberId
    ) {
        auto iterator = members_.find(memberId);

        if (iterator == members_.end()) {
            throw std::out_of_range(
                "Unknown member ID: " + memberId
            );
        }

        return iterator->second;
    }

public:
    explicit Library(
        std::shared_ptr<Notifier> notifier
    )
        : notifier_(std::move(notifier)) {

        if (!notifier_) {
            throw std::invalid_argument(
                "Notifier dependency cannot be null."
            );
        }
    }

    void addBook(Book book) {
        const std::string isbn = book.isbn();

        if (books_.find(isbn) != books_.end()) {
            throw std::logic_error(
                "Book already exists: " + isbn
            );
        }

        books_.emplace(
            isbn,
            std::move(book)
        );
    }

    void registerMember(
        LibraryMember member
    ) {
        const std::string id = member.memberId();

        if (members_.find(id) != members_.end()) {
            throw std::logic_error(
                "Member already exists: " + id
            );
        }

        members_.emplace(
            id,
            std::move(member)
        );
    }

    std::string borrowBook(
        const std::string& memberId,
        const std::string& isbn
    ) {
        LibraryMember& member = getMember(memberId);
        getBook(isbn);

        if (member.hasBorrowed(isbn)) {
            throw std::logic_error(
                "Member already borrowed this book."
            );
        }

        if (member.borrowedCount() >=
            MAX_BOOKS_PER_MEMBER) {

            throw std::logic_error(
                "Member borrowing limit reached."
            );
        }

        if (isBookBorrowed(isbn)) {
            throw std::logic_error(
                "Book is currently unavailable."
            );
        }

        member.borrow(isbn);

        std::string message =
            member.name() +
            " borrowed book " +
            isbn +
            ".";

        notifier_->send(message);

        return message;
    }

    std::string returnBook(
        const std::string& memberId,
        const std::string& isbn
    ) {
        LibraryMember& member = getMember(memberId);

        if (!member.hasBorrowed(isbn)) {
            throw std::logic_error(
                "Member has not borrowed this book."
            );
        }

        member.returnBook(isbn);

        std::string message =
            member.name() +
            " returned book " +
            isbn +
            ".";

        notifier_->send(message);

        return message;
    }

    std::vector<std::reference_wrapper<const Book>>
    searchByAuthor(
        const std::string& author
    ) const {
        std::vector<
            std::reference_wrapper<const Book>
        > results;

        for (const auto& entry : books_) {
            const Book& book = entry.second;

            if (book.author().find(author) !=
                std::string::npos) {

                results.push_back(book);
            }
        }

        return results;
    }

    std::vector<
        std::reference_wrapper<const Book>
    > availableBooks() const {

        std::vector<
            std::reference_wrapper<const Book>
        > results;

        for (const auto& entry : books_) {
            const std::string& isbn = entry.first;

            if (!isBookBorrowed(isbn)) {
                results.push_back(entry.second);
            }
        }

        return results;
    }

    std::size_t bookCount() const {
        return books_.size();
    }

    std::size_t memberCount() const {
        return members_.size();
    }
};

// =============================================================================
// 11. STRATEGY PATTERN
// =============================================================================

class PricingStrategy {
public:
    virtual ~PricingStrategy() = default;

    virtual Money calculate(
        const Money& basePrice
    ) const = 0;
};

class RegularPricing : public PricingStrategy {
public:
    Money calculate(
        const Money& basePrice
    ) const override {
        return basePrice;
    }
};

class TenPercentDiscount :
    public PricingStrategy {

public:
    Money calculate(
        const Money& basePrice
    ) const override {

        const long long discountedCents =
            static_cast<long long>(
                std::llround(
                    static_cast<double>(
                        basePrice.cents()
                    ) * 0.90
                )
            );

        return Money(discountedCents);
    }
};

class Checkout {
private:
    std::shared_ptr<
        const PricingStrategy
    > strategy_;

public:
    explicit Checkout(
        std::shared_ptr<
            const PricingStrategy
        > strategy
    )
        : strategy_(std::move(strategy)) {

        if (!strategy_) {
            throw std::invalid_argument(
                "Pricing strategy cannot be null."
            );
        }
    }

    Money finalPrice(
        const Money& basePrice
    ) const {
        if (basePrice.cents() < 0) {
            throw std::invalid_argument(
                "Base price cannot be negative."
            );
        }

        return strategy_->calculate(basePrice);
    }
};

// =============================================================================
// 12. GENERIC OOP UTILITY
// =============================================================================

template <typename T>
class Repository {
private:
    std::vector<T> records_;

public:
    void add(T record) {
        records_.push_back(std::move(record));
    }

    std::size_t size() const {
        return records_.size();
    }

    const T& at(std::size_t index) const {
        if (index >= records_.size()) {
            throw std::out_of_range(
                "Repository index out of range."
            );
        }

        return records_[index];
    }
};

// =============================================================================
// 13. RAII RESOURCE
// =============================================================================

class TransactionGuard {
private:
    std::string resourceName_;
    bool committed_;

public:
    explicit TransactionGuard(
        std::string resourceName
    )
        : resourceName_(std::move(resourceName)),
          committed_(false) {

        std::cout
            << "Transaction started: "
            << resourceName_
            << "\n";
    }

    void commit() {
        committed_ = true;

        std::cout
            << "Transaction committed: "
            << resourceName_
            << "\n";
    }

    ~TransactionGuard() {
        if (!committed_) {
            std::cout
                << "Transaction rolled back automatically: "
                << resourceName_
                << "\n";
        }
    }
};

// =============================================================================
// 14. SIMPLE ASSERTION HELPERS
// =============================================================================

void require(
    bool condition,
    const std::string& message
) {
    if (!condition) {
        throw std::runtime_error(
            "Test failed: " + message
        );
    }
}

template <typename ExceptionType, typename Function>
void requireThrows(Function&& function) {
    try {
        function();
    }
    catch (const ExceptionType&) {
        return;
    }

    throw std::runtime_error(
        "Expected exception was not thrown."
    );
}

// =============================================================================
// MAIN CASE STUDY
// =============================================================================

int runCaseStudy() {
    printSection(
        "Object-Oriented Programming in C++17"
    );

    // -------------------------------------------------------------------------
    // Basic class
    // -------------------------------------------------------------------------

    printSection("1. Classes and Objects");

    Student student(
        "Ananya",
        21
    );

    std::cout
        << student.introduce()
        << "\n";

    // -------------------------------------------------------------------------
    // Encapsulation
    // -------------------------------------------------------------------------

    printSection("2. Encapsulation");

    BankAccount account(
        "Riya",
        1000.0
    );

    account.deposit(500.0);
    account.withdraw(250.0);

    std::cout
        << "Balance: "
        << account.balance()
        << "\n";

    std::cout
        << "Transactions: "
        << account.transactionCount()
        << "\n";

    requireThrows<std::runtime_error>(
        [&account]() {
            account.withdraw(5000.0);
        }
    );

    // -------------------------------------------------------------------------
    // Inheritance and polymorphism
    // -------------------------------------------------------------------------

    printSection(
        "3. Inheritance and Runtime Polymorphism"
    );

    std::vector<
        std::unique_ptr<Vehicle>
    > vehicles;

    vehicles.push_back(
        std::make_unique<Vehicle>("Generic")
    );

    vehicles.push_back(
        std::make_unique<Car>("Toyota")
    );

    vehicles.push_back(
        std::make_unique<ElectricCar>(
            "Tesla",
            75.0
        )
    );

    for (const auto& vehicle : vehicles) {
        std::cout
            << vehicle->move()
            << "\n";
    }

    // -------------------------------------------------------------------------
    // Abstract classes
    // -------------------------------------------------------------------------

    printSection("4. Abstract Classes");

    std::vector<
        std::unique_ptr<Shape>
    > shapes;

    shapes.push_back(
        std::make_unique<Rectangle>(
            10.0,
            5.0
        )
    );

    shapes.push_back(
        std::make_unique<Circle>(3.0)
    );

    std::cout
        << std::fixed
        << std::setprecision(2);

    for (const auto& shape : shapes) {
        std::cout
            << "Area: "
            << shape->area()
            << ", perimeter: "
            << shape->perimeter()
            << "\n";
    }

    // -------------------------------------------------------------------------
    // Composition
    // -------------------------------------------------------------------------

    printSection("5. Composition");

    ComposedCar composedCar("Honda");

    composedCar.start();

    std::cout
        << composedCar.brand()
        << " running: "
        << std::boolalpha
        << composedCar.isRunning()
        << "\n";

    composedCar.stop();

    // -------------------------------------------------------------------------
    // Operator overloading
    // -------------------------------------------------------------------------

    printSection("6. Operator Overloading");

    Money first(1500);
    Money second(2500);

    Money total = first + second;

    std::cout
        << "First: "
        << first
        << "\n";

    std::cout
        << "Second: "
        << second
        << "\n";

    std::cout
        << "Total: "
        << total
        << "\n";

    require(
        total == Money(4000),
        "Money addition"
    );

    // -------------------------------------------------------------------------
    // Industry case study setup
    // -------------------------------------------------------------------------

    printSection(
        "7. Library Management System"
    );

    auto notifier =
        std::make_shared<ConsoleNotifier>();

    Library library(notifier);

    library.addBook(
        Book(
            "978-1",
            "Clean Code",
            "Robert C. Martin"
        )
    );

    library.addBook(
        Book(
            "978-2",
            "The Pragmatic Programmer",
            "Andrew Hunt"
        )
    );

    library.addBook(
        Book(
            "978-3",
            "C++ Primer",
            "Stanley Lippman"
        )
    );

    library.registerMember(
        LibraryMember(
            "M001",
            "Ananya"
        )
    );

    library.registerMember(
        LibraryMember(
            "M002",
            "Kabir"
        )
    );

    std::cout
        << "Books: "
        << library.bookCount()
        << "\n";

    std::cout
        << "Members: "
        << library.memberCount()
        << "\n";

    // -------------------------------------------------------------------------
    // Successful borrowing
    // -------------------------------------------------------------------------

    printSection(
        "8. Borrowing and Returning"
    );

    library.borrowBook(
        "M001",
        "978-1"
    );

    library.borrowBook(
        "M002",
        "978-2"
    );

    // -------------------------------------------------------------------------
    // Failure condition
    // -------------------------------------------------------------------------

    printSection(
        "9. Failure Conditions"
    );

    try {
        library.borrowBook(
            "M002",
            "978-1"
        );
    }
    catch (const std::exception& error) {
        std::cout
            << "Expected error: "
            << error.what()
            << "\n";
    }

    // -------------------------------------------------------------------------
    // Search
    // -------------------------------------------------------------------------

    printSection(
        "10. Searching"
    );

    auto searchResults =
        library.searchByAuthor("Andrew");

    for (const Book& book : searchResults) {
        std::cout
            << book.title()
            << " by "
            << book.author()
            << "\n";
    }

    // -------------------------------------------------------------------------
    // Available books
    // -------------------------------------------------------------------------

    printSection(
        "11. Available Books"
    );

    auto available =
        library.availableBooks();

    for (const Book& book : available) {
        std::cout
            << book.isbn()
            << " | "
            << book.title()
            << "\n";
    }

    // -------------------------------------------------------------------------
    // Return
    // -------------------------------------------------------------------------

    library.returnBook(
        "M001",
        "978-1"
    );

    // -------------------------------------------------------------------------
    // Dependency injection
    // -------------------------------------------------------------------------

    printSection(
        "12. Dependency Injection"
    );

    std::shared_ptr<
        const PricingStrategy
    > pricingStrategy =
        std::make_shared<
            TenPercentDiscount
        >();

    Checkout checkout(
        pricingStrategy
    );

    Money productPrice(10000);

    std::cout
        << "Original price: "
        << productPrice
        << "\n";

    std::cout
        << "Final price: "
        << checkout.finalPrice(productPrice)
        << "\n";

    // -------------------------------------------------------------------------
    // Factory-like polymorphic creation
    // -------------------------------------------------------------------------

    printSection(
        "13. Polymorphic Service Collection"
    );

    std::vector<
        std::unique_ptr<PricingStrategy>
    > pricingStrategies;

    pricingStrategies.push_back(
        std::make_unique<RegularPricing>()
    );

    pricingStrategies.push_back(
        std::make_unique<TenPercentDiscount>()
    );

    for (const auto& strategy : pricingStrategies) {
        std::cout
            << "Calculated price: "
            << strategy->calculate(productPrice)
            << "\n";
    }

    // -------------------------------------------------------------------------
    // Generic repository
    // -------------------------------------------------------------------------

    printSection(
        "14. Template-Based Repository"
    );

    Repository<Book> repository;

    repository.add(
        Book(
            "R-1",
            "Design Patterns",
            "Erich Gamma"
        )
    );

    repository.add(
        Book(
            "R-2",
            "Effective C++",
            "Scott Meyers"
        )
    );

    std::cout
        << "Repository size: "
        << repository.size()
        << "\n";

    std::cout
        << "First record: "
        << repository.at(0).title()
        << "\n";

    // -------------------------------------------------------------------------
    // RAII
    // -------------------------------------------------------------------------

    printSection(
        "15. RAII and Deterministic Resource Management"
    );

    {
        TransactionGuard transaction(
            "library-borrow-operation"
        );

        transaction.commit();
    }

    {
        TransactionGuard transaction(
            "simulated-failure"
        );

        // Destruction occurs automatically at scope exit.
        // Since commit() is not called, rollback is automatic.
    }

    // -------------------------------------------------------------------------
    // Edge cases
    // -------------------------------------------------------------------------

    printSection(
        "16. Edge Cases"
    );

    requireThrows<std::invalid_argument>(
        []() {
            BankAccount invalid(
                "Invalid",
                -100.0
            );
        }
    );

    requireThrows<std::out_of_range>(
        [&library]() {
            library.borrowBook(
                "UNKNOWN",
                "978-1"
            );
        }
    );

    requireThrows<std::out_of_range>(
        [&repository]() {
            repository.at(100);
        }
    );

    // -------------------------------------------------------------------------
    // Performance demonstration
    // -------------------------------------------------------------------------

    printSection(
        "17. Performance Considerations"
    );

    constexpr std::size_t iterations =
        100000;

    auto start =
        std::chrono::high_resolution_clock::now();

    long long accumulator = 0;

    for (std::size_t index = 0;
         index < iterations;
         ++index) {

        accumulator +=
            static_cast<long long>(index);
    }

    auto end =
        std::chrono::high_resolution_clock::now();

    const auto elapsed =
        std::chrono::duration_cast<
            std::chrono::microseconds
        >(end - start);

    std::cout
        << "Accumulator: "
        << accumulator
        << "\n";

    std::cout
        << "Loop time: "
        << elapsed.count()
        << " microseconds\n";

    // -------------------------------------------------------------------------
    // Complexity discussion through actual data structures
    // -------------------------------------------------------------------------

    printSection(
        "18. Data Structure and Complexity Considerations"
    );

    std::cout
        << "unordered_map average lookup: O(1)\n"
        << "set lookup/insertion: O(log n)\n"
        << "vector indexed access: O(1)\n"
        << "vector linear search: O(n)\n"
        << "Library availability scan in this design: O(M * B)\n"
        << "where M = members and B = borrowed-book checks.\n";

    // -------------------------------------------------------------------------
    // Final validation
    // -------------------------------------------------------------------------

    printSection(
        "19. Integrated Test Result"
    );

    require(
        library.bookCount() == 3,
        "Library should contain three books."
    );

    require(
        library.memberCount() == 2,
        "Library should contain two members."
    );

    require(
        checkout.finalPrice(Money(10000))
            == Money(9000),
        "Ten percent discount calculation."
    );

    std::cout
        << "All integrated OOP checks passed.\n";

    return 0;
}

} // namespace oop_demo

int main() {
    try {
        return oop_demo::runCaseStudy();
    }
    catch (const std::exception& error) {
        std::cerr
            << "Fatal error: "
            << error.what()
            << "\n";

        return 1;
    }
}
