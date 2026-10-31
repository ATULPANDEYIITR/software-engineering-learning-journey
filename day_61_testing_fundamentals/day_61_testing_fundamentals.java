import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class TestingFundamentals {

    enum TestLevel {
        UNIT, INTEGRATION, SYSTEM
    }

    record User(int id, String name, String email) {
        User {
            if (id <= 0) {
                throw new ValidationException("id must be positive");
            }
            if (name == null || name.isBlank()) {
                throw new ValidationException("name is required");
            }
            if (!isValidEmail(email)) {
                throw new ValidationException("invalid email");
            }
        }
    }

    record TestCase(String name, TestLevel level, TestAction action) {}

    @FunctionalInterface
    interface TestAction {
        void run() throws Exception;
    }

    static class ValidationException extends RuntimeException {
        ValidationException(String message) {
            super(message);
        }
    }

    static class UserAlreadyExistsException extends RuntimeException {
        UserAlreadyExistsException(String message) {
            super(message);
        }
    }

    static class UserNotFoundException extends RuntimeException {
        UserNotFoundException(String message) {
            super(message);
        }
    }

    interface UserRepository {
        void save(User user);
        Optional<User> findById(int id);
    }

    static final class InMemoryUserRepository implements UserRepository {
        private final Map<Integer, User> users = new ConcurrentHashMap<>();

        @Override
        public void save(User user) {
            if (users.putIfAbsent(user.id(), user) != null) {
                throw new UserAlreadyExistsException(
                    "User " + user.id() + " already exists"
                );
            }
        }

        @Override
        public Optional<User> findById(int id) {
            return Optional.ofNullable(users.get(id));
        }
    }

    static final class UserService {
        private final UserRepository repository;

        UserService(UserRepository repository) {
            this.repository = repository;
        }

        User register(User user) {
            repository.save(user);
            return user;
        }

        User getUser(int id) {
            return repository.findById(id)
                .orElseThrow(() ->
                    new UserNotFoundException("User " + id + " not found"));
        }

        Path exportUser(int id, Path directory) throws IOException {
            User user = getUser(id);
            Files.createDirectories(directory);

            Path output = directory.resolve("user-" + id + ".txt");

            String content = """
                id=%d
                name=%s
                email=%s
                """.formatted(user.id(), user.name(), user.email());

            Files.writeString(
                output,
                content,
                StandardCharsets.UTF_8
            );

            return output;
        }
    }

    interface DiscountPolicy {
        double calculate(double total, double percentage);
    }

    static final class StandardDiscountPolicy implements DiscountPolicy {
        @Override
        public double calculate(double total, double percentage) {
            if (!Double.isFinite(total) || total < 0) {
                throw new ValidationException(
                    "total must be a finite non-negative number"
                );
            }
            if (!Double.isFinite(percentage)
                || percentage < 0
                || percentage > 100) {
                throw new ValidationException(
                    "percentage must be between 0 and 100"
                );
            }

            return Math.round(total * (1 - percentage / 100.0) * 100.0)
                / 100.0;
        }
    }

    static boolean isValidEmail(String email) {
        if (email == null || email.isBlank() || email.contains(" ")) {
            return false;
        }

        int at = email.indexOf('@');
        int dot = email.lastIndexOf('.');

        return at > 0
            && dot > at + 1
            && dot < email.length() - 1;
    }

    static void assertTrue(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    static void assertEquals(Object expected, Object actual) {
        if (!java.util.Objects.equals(expected, actual)) {
            throw new AssertionError(
                "Expected " + expected + " but got " + actual
            );
        }
    }

    static <T extends Throwable> void assertThrows(
        Class<T> expected,
        TestAction action
    ) throws Exception {
        try {
            action.run();
        } catch (Throwable error) {
            if (expected.isInstance(error)) {
                return;
            }
            throw new AssertionError(
                "Expected " + expected.getSimpleName()
                    + " but got " + error.getClass().getSimpleName(),
                error
            );
        }

        throw new AssertionError(
            "Expected " + expected.getSimpleName()
                + " but no exception was thrown"
        );
    }

    static void unitTests() throws Exception {
        assertTrue(
            isValidEmail("user@example.com"),
            "valid email rejected"
        );
        assertTrue(
            !isValidEmail("user@example"),
            "invalid email accepted"
        );
        assertEquals(800.0,
            new StandardDiscountPolicy().calculate(1000, 20));

        assertThrows(
            ValidationException.class,
            () -> new StandardDiscountPolicy().calculate(-1, 10)
        );

        assertThrows(
            ValidationException.class,
            () -> new StandardDiscountPolicy().calculate(100, 101)
        );
    }

    static void integrationTests() throws Exception {
        UserRepository repository = new InMemoryUserRepository();
        UserService service = new UserService(repository);

        User user = new User(1, "Atul", "atul@example.com");
        service.register(user);

        assertEquals(user, repository.findById(1).orElseThrow());
        assertEquals(user, service.getUser(1));

        assertThrows(
            UserAlreadyExistsException.class,
            () -> service.register(user)
        );

        assertThrows(
            UserNotFoundException.class,
            () -> service.getUser(999)
        );
    }

    static void systemTests() throws Exception {
        UserRepository repository = new InMemoryUserRepository();
        UserService service = new UserService(repository);

        service.register(
            new User(7, "System User", "system@example.com")
        );

        Path directory = Files.createTempDirectory("testing-fundamentals-");

        try {
            Path file = service.exportUser(7, directory);
            String content = Files.readString(file);

            assertTrue(
                content.contains("id=7"),
                "exported ID missing"
            );
            assertTrue(
                content.contains("System User"),
                "exported name missing"
            );
            assertTrue(
                content.contains("system@example.com"),
                "exported email missing"
            );

            assertThrows(
                UserNotFoundException.class,
                () -> service.exportUser(999, directory)
            );
        } finally {
            try (var paths = Files.walk(directory)) {
                paths.sorted(java.util.Comparator.reverseOrder())
                    .forEach(path -> {
                        try {
                            Files.deleteIfExists(path);
                        } catch (IOException error) {
                            throw new RuntimeException(error);
                        }
                    });
            }
        }
    }

    static void runSuite(
        String suiteName,
        List<TestCase> tests
    ) {
        int passed = 0;

        for (TestCase test : tests) {
            try {
                test.action().run();
                passed++;
                System.out.printf(
                    "[PASS] %-12s %-15s %s%n",
                    test.level(),
                    suiteName,
                    test.name()
                );
            } catch (Throwable error) {
                System.err.printf(
                    "[FAIL] %-12s %-15s %s: %s%n",
                    test.level(),
                    suiteName,
                    test.name(),
                    error.getMessage()
                );
                throw new AssertionError(
                    "Test suite failed: " + suiteName,
                    error
                );
            }
        }

        System.out.printf(
            "Suite %s: %d/%d passed%n",
            suiteName,
            passed,
            tests.size()
        );
    }

    public static void main(String[] args) throws Exception {
        List<TestCase> tests = new ArrayList<>();

        tests.add(new TestCase(
            "validation and discount",
            TestLevel.UNIT,
            TestingFundamentals::unitTests
        ));

        tests.add(new TestCase(
            "repository and service collaboration",
            TestLevel.INTEGRATION,
            TestingFundamentals::integrationTests
        ));

        tests.add(new TestCase(
            "registration and file export",
            TestLevel.SYSTEM,
            TestingFundamentals::systemTests
        ));

        runSuite("Testing Fundamentals", tests);

        System.out.println("""
            
            Testing boundaries:
            - Unit tests isolate business rules and validation.
            - Integration tests verify service and repository collaboration.
            - System tests exercise a complete user-facing workflow.
            - Records provide immutable domain values.
            - Repository interfaces isolate persistence from business logic.
            - Explicit exceptions make failure states testable.
            """);
    }
}
