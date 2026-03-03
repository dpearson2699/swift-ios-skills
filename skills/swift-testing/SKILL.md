---
name: swift-testing
description: "Swift Testing framework guide for writing tests with @Test, @Suite, #expect, #require, confirmation, parameterized tests, test tags, traits, withKnownIssue, XCTest UI testing, XCUITest, test plan, mocking, test doubles, testable architecture, snapshot testing, async test patterns, test organization, and test-driven development in Swift. Use when writing or migrating tests with Swift Testing framework, implementing parameterized tests, working with test traits, converting XCTest to Swift Testing, or setting up test organization and mocking patterns."
---

# Swift Testing

Swift Testing is the modern testing framework for Swift (Xcode 16+, Swift 6+). Prefer it over XCTest for all new unit tests. Use XCTest only for UI tests, performance benchmarks, and snapshot tests.

## Basic Tests

```swift
import Testing

@Test("User can update their display name")
func updateDisplayName() {
    var user = User(name: "Alice")
    user.name = "Bob"
    #expect(user.name == "Bob")
}
```

## @Test Traits

```swift
@Test("Validates email format")                                    // display name
@Test(.tags(.validation, .email))                                  // tags
@Test(.disabled("Server migration in progress"))                   // disabled
@Test(.enabled(if: ProcessInfo.processInfo.environment["CI"] != nil)) // conditional
@Test(.bug("https://github.com/org/repo/issues/42"))               // bug reference
@Test(.timeLimit(.minutes(1)))                                     // time limit
@Test("Timeout handling", .tags(.networking), .timeLimit(.seconds(30))) // combined
```

## #expect and #require

```swift
// #expect records failure but continues execution
#expect(result == 42)
#expect(name.isEmpty == false)
#expect(items.count > 0, "Items should not be empty")

// #expect with error type checking
#expect(throws: ValidationError.self) {
    try validate(email: "not-an-email")
}

// #expect with specific error value
#expect {
    try validate(email: "")
} throws: { error in
    guard let err = error as? ValidationError else { return false }
    return err == .empty
}

// #require records failure AND stops test (like XCTUnwrap)
let user = try #require(await fetchUser(id: 1))
#expect(user.name == "Alice")

// #require for optionals -- unwraps or fails
let first = try #require(items.first)
#expect(first.isValid)
```

**Rule: Use `#require` when subsequent assertions depend on the value. Use `#expect` for independent checks.**

## @Suite and Test Organization

```swift
@Suite("Authentication Tests")
struct AuthTests {
    let auth: AuthService

    // init() runs before EACH test (like setUp in XCTest)
    init() {
        auth = AuthService(store: MockKeychain())
    }

    @Test func loginWithValidCredentials() async throws {
        let result = try await auth.login(email: "test@test.com", password: "pass123")
        #expect(result.isAuthenticated)
    }

    @Test func loginWithInvalidPassword() async throws {
        #expect(throws: AuthError.invalidCredentials) {
            try await auth.login(email: "test@test.com", password: "wrong")
        }
    }
}
```

Suites can be nested. Tags applied to a suite are inherited by all tests in that suite.

## Parameterized Tests

```swift
@Test("Email validation", arguments: [
    ("user@example.com", true),
    ("user@", false),
    ("@example.com", false),
    ("", false),
])
func validateEmail(email: String, isValid: Bool) {
    #expect(EmailValidator.isValid(email) == isValid)
}

// From CaseIterable
@Test(arguments: Currency.allCases)
func currencyHasSymbol(currency: Currency) {
    #expect(currency.symbol.isEmpty == false)
}

// Two collections: cartesian product of all combinations
@Test(arguments: [1, 2, 3], ["a", "b"])
func combinations(number: Int, letter: String) {
    #expect(number > 0)
}

// Use zip for 1:1 pairing instead of cartesian product
@Test(arguments: zip(["USD", "EUR"], ["$", "€"]))
func currencySymbols(code: String, symbol: String) {
    #expect(Currency(code: code).symbol == symbol)
}
```

Each argument combination runs as an independent test case reported separately.

## Confirmation (Async Event Testing)

Replace XCTest's `expectation`/`fulfill`/`waitForExpectations` with `confirmation`:
```swift
@Test func notificationPosted() async {
    await confirmation("Received notification") { confirm in
        let observer = NotificationCenter.default.addObserver(
            forName: .userLoggedIn, object: nil, queue: .main
        ) { _ in confirm() }
        await authService.login()
        NotificationCenter.default.removeObserver(observer)
    }
}

// Exact count -- confirm must be called exactly 3 times
await confirmation("Items processed", expectedCount: 3) { confirm in
    processor.onItemComplete = { _ in confirm() }
    await processor.processAll()
}

// Range-based: at least once
await confirmation("Orders placed", expectedCount: 1...) { confirm in
    truck.orderHandler = { _ in confirm() }
    await truck.operate()
}

// Confirm something does NOT happen
await confirmation("No errors", expectedCount: 0) { confirm in
    calculator.errorHandler = { _ in confirm() }
    await calculator.compute()
}
```

## Tags

Define custom tags for filtering and organizing test runs:

```swift
extension Tag {
    @Tag static var networking: Self
    @Tag static var database: Self
    @Tag static var slow: Self
    @Tag static var critical: Self
}

@Test(.tags(.networking, .slow))
func downloadLargeFile() async throws { ... }

// Tags on suites are inherited by all contained tests
@Suite(.tags(.database))
struct DatabaseTests {
    @Test func insertUser() { ... }  // inherits .database tag
}
```

Tags must be declared as static members in an extension on `Tag` using the `@Tag` macro.

## Known Issues

Mark expected failures so they do not cause test failure:

```swift
withKnownIssue("Propane tank is empty") {
    #expect(truck.grill.isHeating)
}

// Intermittent / flaky failures
withKnownIssue(isIntermittent: true) {
    #expect(service.isReachable)
}

// Conditional known issue
withKnownIssue {
    #expect(foodTruck.grill.isHeating)
} when: {
    !hasPropane
}

// Match specific issues only
try withKnownIssue {
    let level = try #require(foodTruck.batteryLevel)
    #expect(level >= 0.8)
} matching: { issue in
    guard case .expectationFailed(let expectation) = issue.kind else { return false }
    return expectation.isRequired
}
```

If no known issues are recorded, Swift Testing records a distinct issue notifying you the problem may be resolved.

## TestScoping (Custom Test Lifecycle)

Consolidate setup/teardown logic (Swift 6.1+, Xcode 16.3+):

```swift
struct DatabaseFixture: TestScoping {
    func provideScope(
        for test: Test, testCase: Test.Case?,
        performing body: @Sendable () async throws -> Void
    ) async throws {
        let db = try await TestDatabase.create()
        try await body()
        try await db.destroy()
    }
}
```

Use `.serialized` on suites where tests share mutable state and cannot run concurrently.

## Mocking and Test Doubles

Every external dependency should be behind a protocol. Inject dependencies -- never hardcode them:

```swift
protocol UserRepository: Sendable {
    func fetch(id: String) async throws -> User
    func save(_ user: User) async throws
}

// Test double
struct MockUserRepository: UserRepository {
    var users: [String: User] = [:]
    var fetchError: Error?
    func fetch(id: String) async throws -> User {
        if let error = fetchError { throw error }
        guard let user = users[id] else { throw NotFoundError() }
        return user
    }
    func save(_ user: User) async throws { }
}
```

## Testable Architecture

```swift
@Observable
class ProfileViewModel {
    private let repository: UserRepository
    var user: User?
    var error: Error?
    init(repository: UserRepository) { self.repository = repository }
    func load() async {
        do { user = try await repository.fetch(id: currentUserID) }
        catch { self.error = error }
    }
}

@Test func loadUserSuccess() async {
    let mock = MockUserRepository(users: ["1": User(name: "Alice")])
    let vm = ProfileViewModel(repository: mock)
    await vm.load()
    #expect(vm.user?.name == "Alice")
}
```

### SwiftUI Environment Injection

```swift
private struct UserRepositoryKey: EnvironmentKey {
    static let defaultValue: any UserRepository = RemoteUserRepository()
}
extension EnvironmentValues {
    var userRepository: any UserRepository {
        get { self[UserRepositoryKey.self] }
        set { self[UserRepositoryKey.self] = newValue }
    }
}
// In previews and tests:
ContentView().environment(\.userRepository, MockUserRepository())
```

## Async and Concurrent Test Patterns

Swift Testing supports async natively. Use `@MainActor` for tests touching MainActor-isolated code:

```swift
@Test func fetchUser() async throws {
    let service = UserService(repository: MockUserRepository())
    let user = try await service.fetch(id: "1")
    #expect(user.name == "Alice")
}

@Test @MainActor func viewModelUpdatesOnMainActor() async {
    let vm = ProfileViewModel(repository: MockUserRepository())
    await vm.load()
    #expect(vm.user != nil)
}
```

### Clock Injection

Inject a clock protocol to test time-dependent code without real delays:

```swift
protocol AppClock: Sendable { func sleep(for duration: Duration) async throws }
struct ImmediateClock: AppClock { func sleep(for duration: Duration) async throws { } }
```

### Testing Error Paths

```swift
@Test func fetchUserNetworkError() async {
    var mock = MockUserRepository()
    mock.fetchError = URLError(.notConnectedToInternet)
    let vm = ProfileViewModel(repository: mock)
    await vm.load()
    #expect(vm.user == nil)
    #expect(vm.error is URLError)
}
```

## XCTest: UI Testing

Swift Testing does not support UI testing. Use XCTest with XCUITest for all UI tests.

```swift
class LoginUITests: XCTestCase {
    let app = XCUIApplication()
    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launchArguments = ["--ui-testing"]
        app.launch()
    }
    func testLoginFlow() throws {
        let emailField = app.textFields["Email"]
        XCTAssertTrue(emailField.waitForExistence(timeout: 5))
        emailField.tap(); emailField.typeText("user@test.com")
        app.secureTextFields["Password"].tap()
        app.secureTextFields["Password"].typeText("password123")
        app.buttons["Sign In"].tap()
        XCTAssertTrue(app.staticTexts["Welcome"].waitForExistence(timeout: 10))
    }
}
```

### Page Object Pattern

Encapsulate UI element queries in page objects for reusable, readable UI tests:

```swift
struct LoginPage {
    let app: XCUIApplication
    var emailField: XCUIElement { app.textFields["Email"] }
    var passwordField: XCUIElement { app.secureTextFields["Password"] }
    var signInButton: XCUIElement { app.buttons["Sign In"] }
    @discardableResult
    func login(email: String, password: String) -> HomePage {
        emailField.tap(); emailField.typeText(email)
        passwordField.tap(); passwordField.typeText(password)
        signInButton.tap()
        return HomePage(app: app)
    }
}
```

### Performance Testing (XCTest)

```swift
func testFeedParsingPerformance() throws {
    let data = try loadFixture("large-feed.json")
    let metrics: [XCTMetric] = [XCTClockMetric(), XCTMemoryMetric()]
    measure(metrics: metrics) {
        _ = try? FeedParser.parse(data)
    }
}
```

## Snapshot Testing

Use swift-snapshot-testing (pointfreeco) for visual regression. Requires XCTest:

```swift
import SnapshotTesting
import XCTest

class ProfileViewSnapshotTests: XCTestCase {
    func testProfileView() {
        let view = ProfileView(user: .preview)
        assertSnapshot(of: view, as: .image(layout: .device(config: .iPhone13)))

        // Dark mode
        assertSnapshot(of: view.environment(\.colorScheme, .dark),
                       as: .image(layout: .device(config: .iPhone13)), named: "dark")

        // Large Dynamic Type
        assertSnapshot(of: view.environment(\.dynamicTypeSize, .accessibility3),
                       as: .image(layout: .device(config: .iPhone13)), named: "largeText")
    }
}
```

Always test Dark Mode and large Dynamic Type in snapshots.

## Test File Organization

```
Tests/AppTests/          # Swift Testing (Models/, ViewModels/, Services/)
Tests/AppUITests/        # XCTest UI tests (Pages/, Flows/)
Tests/Fixtures/          # Test data (JSON, images)
Tests/Mocks/             # Shared mock implementations
```

Name test files `<TypeUnderTest>Tests.swift`. Describe behavior in function names: `fetchUserReturnsNilOnNetworkError()` not `testFetchUser()`. Name mocks `Mock<ProtocolName>`.

### What to Test

**Always test:** business logic, validation rules, state transitions in view models, error handling paths, edge cases (empty collections, nil, boundaries), async success and failure, Task cancellation.

**Skip:** SwiftUI view body layout (use snapshots), simple property forwarding, Apple framework behavior, private methods (test through public API).

## Common Mistakes

1. **Testing implementation, not behavior.** Test what the code does, not how.
2. **No error path tests.** If a function can throw, test the throw path.
3. **Flaky async tests.** Use `confirmation` with expected counts, not `sleep` calls.
4. **Shared mutable state between tests.** Each test sets up its own state via `init()` in `@Suite`.
5. **Missing accessibility identifiers in UI tests.** XCUITest queries rely on them.
6. **Using `sleep` in tests.** Use `confirmation`, clock injection, or `withKnownIssue`.
7. **Not testing cancellation.** If code supports `Task` cancellation, verify it cancels cleanly.
8. **Mixing XCTest and Swift Testing in one file.** Keep them in separate files.
9. **Non-Sendable test helpers shared across tests.** Ensure test helper types are Sendable when shared across concurrent test cases. Annotate MainActor-dependent test code with `@MainActor`.

## Test Attachments

Attach diagnostic data to test results for debugging failures:

```swift
@Test func generateReport() async throws {
    let report = try generateReport()
    // Attach the output for later inspection
    Attachment(report.data, named: "report.json").record()
    #expect(report.isValid)
}

// Attach from a file URL
@Test func processImage() async throws {
    let output = try processImage()
    try await Attachment(contentsOf: output.url, named: "result.png")
        .record()
}
```

Attachments support any `Attachable` type and images via `AttachableAsImage`.

## Exit Testing

Test code that calls `exit()`, `fatalError()`, or `preconditionFailure()`:

```swift
@Test func invalidInputCausesExit() async {
    await #expect(processExitsWith: .failure) {
        processInvalidInput()  // calls fatalError()
    }
}
```

## Review Checklist

- [ ] All new tests use Swift Testing (`@Test`, `#expect`), not XCTest assertions
- [ ] Test names describe behavior (`fetchUserReturnsNilOnNetworkError` not `testFetchUser`)
- [ ] Error paths have dedicated tests
- [ ] Async tests use `confirmation()`, not `Task.sleep`
- [ ] Parameterized tests used for repetitive variations
- [ ] Tags applied for filtering (`.critical`, `.slow`)
- [ ] Mocks conform to protocols, not subclass concrete types
- [ ] No shared mutable state between tests
- [ ] Cancellation tested for cancellable async operations

## MCP Integration

- **xcodebuildmcp**: Build and run tests directly — full suites, individual functions, tag-filtered runs.
- **apple-docs MCP**: Verify Swift Testing APIs at `/documentation/Testing`.
