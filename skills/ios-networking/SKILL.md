---
name: ios-networking
description: "Build, review, or improve networking code in iOS/macOS apps using URLSession with async/await, structured concurrency, and modern Swift patterns. Use when working with REST APIs, downloading files, uploading data, WebSocket connections, pagination, retry logic, request middleware, caching, background transfers, or network reachability monitoring. Trigger for any task involving HTTP requests, API clients, network error handling, or data fetching in Swift apps."
---

# iOS Networking

Modern networking patterns for iOS 26+ using URLSession with async/await and
structured concurrency. All examples target Swift 6.2. No third-party
dependencies required -- URLSession covers the vast majority of networking
needs.

## Core URLSession async/await

URLSession gained native async/await overloads in iOS 15. These are the
only networking APIs to use in new code. Never use completion-handler
variants in new projects.

### Data Requests

```swift
// Basic GET
let (data, response) = try await URLSession.shared.data(from: url)

// With a configured URLRequest
var request = URLRequest(url: url)
request.httpMethod = "POST"
request.setValue("application/json", forHTTPHeaderField: "Content-Type")
request.httpBody = try JSONEncoder().encode(payload)
request.timeoutInterval = 30
request.cachePolicy = .reloadIgnoringLocalCacheData

let (data, response) = try await URLSession.shared.data(for: request)
```

### Response Validation

Always validate the HTTP status code before decoding. URLSession does not
throw for 4xx/5xx responses -- it only throws for transport-level failures.

```swift
guard let httpResponse = response as? HTTPURLResponse else {
    throw NetworkError.invalidResponse
}

guard (200..<300).contains(httpResponse.statusCode) else {
    throw NetworkError.httpError(
        statusCode: httpResponse.statusCode,
        data: data
    )
}
```

### JSON Decoding with Codable

```swift
func fetch<T: Decodable>(_ type: T.Type, from url: URL) async throws -> T {
    let (data, response) = try await URLSession.shared.data(from: url)

    guard let httpResponse = response as? HTTPURLResponse,
          (200..<300).contains(httpResponse.statusCode) else {
        throw NetworkError.invalidResponse
    }

    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    return try decoder.decode(T.self, from: data)
}
```

### Downloads and Uploads

Use `download(for:)` for large files -- it streams to disk instead of
loading the entire payload into memory.

```swift
// Download to a temporary file
let (localURL, response) = try await URLSession.shared.download(for: request)

// Move from temp location before the method returns
let destination = documentsDirectory.appendingPathComponent("file.zip")
try FileManager.default.moveItem(at: localURL, to: destination)
```

```swift
// Upload data
let (data, response) = try await URLSession.shared.upload(for: request, from: bodyData)

// Upload from file
let (data, response) = try await URLSession.shared.upload(for: request, fromFile: fileURL)
```

### Streaming with AsyncBytes

Use `bytes(for:)` for streaming responses, progress tracking, or
line-delimited data (e.g., server-sent events).

```swift
let (bytes, response) = try await URLSession.shared.bytes(for: request)

for try await line in bytes.lines {
    // Process each line as it arrives (e.g., SSE stream)
    handleEvent(line)
}
```

## API Client Architecture

### Protocol-Based Client

Define a protocol for testability. This lets you swap implementations in
tests without mocking URLSession directly.

```swift
protocol APIClientProtocol: Sendable {
    func fetch<T: Decodable & Sendable>(
        _ type: T.Type,
        endpoint: Endpoint
    ) async throws -> T

    func send<T: Decodable & Sendable>(
        _ type: T.Type,
        endpoint: Endpoint,
        body: some Encodable & Sendable
    ) async throws -> T
}
```

```swift
struct Endpoint: Sendable {
    let path: String
    var method: String = "GET"
    var queryItems: [URLQueryItem] = []
    var headers: [String: String] = [:]

    func url(relativeTo baseURL: URL) -> URL {
        var components = URLComponents(
            url: baseURL.appendingPathComponent(path),
            resolvingAgainstBaseURL: true
        )!
        if !queryItems.isEmpty {
            components.queryItems = queryItems
        }
        return components.url!
    }
}
```

The client accepts a `baseURL`, optional custom `URLSession`, `JSONDecoder`,
and an array of `RequestMiddleware` interceptors. Each method builds a
`URLRequest` from the endpoint, applies middleware, executes the request,
validates the status code, and decodes the result. See
`references/urlsession-patterns.md` for the complete `APIClient` implementation
with convenience methods, request builder, and test setup.

### Lightweight Closure-Based Client

For apps using the MV pattern, use closure-based clients for testability
and SwiftUI preview support. See `references/lightweight-clients.md` for
the full pattern (struct of async closures, injected via init).

### Request Middleware / Interceptors

Middleware transforms requests before they are sent. Use this for
authentication, logging, analytics headers, and similar cross-cutting
concerns.

```swift
protocol RequestMiddleware: Sendable {
    func prepare(_ request: URLRequest) async throws -> URLRequest
}
```

```swift
struct AuthMiddleware: RequestMiddleware {
    let tokenProvider: @Sendable () async throws -> String

    func prepare(_ request: URLRequest) async throws -> URLRequest {
        var request = request
        let token = try await tokenProvider()
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        return request
    }
}
```

### Token Refresh Flow

Handle 401 responses by refreshing the token and retrying once.

```swift
func fetchWithTokenRefresh<T: Decodable & Sendable>(
    _ type: T.Type,
    endpoint: Endpoint,
    tokenStore: TokenStore
) async throws -> T {
    do {
        return try await fetch(type, endpoint: endpoint)
    } catch NetworkError.httpError(statusCode: 401, _) {
        try await tokenStore.refreshToken()
        return try await fetch(type, endpoint: endpoint)
    }
}
```

## Error Handling

### Structured Error Types

```swift
enum NetworkError: Error, Sendable {
    case invalidResponse
    case httpError(statusCode: Int, data: Data)
    case decodingFailed(Error)
    case noConnection
    case timedOut
    case cancelled

    /// Map a URLError to a typed NetworkError
    static func from(_ urlError: URLError) -> NetworkError {
        switch urlError.code {
        case .notConnectedToInternet, .networkConnectionLost:
            return .noConnection
        case .timedOut:
            return .timedOut
        case .cancelled:
            return .cancelled
        default:
            return .httpError(statusCode: -1, data: Data())
        }
    }
}
```

### Key URLError Cases

| URLError Code | Meaning | Action |
|---|---|---|
| `.notConnectedToInternet` | Device offline | Show offline UI, queue for retry |
| `.networkConnectionLost` | Connection dropped mid-request | Retry with backoff |
| `.timedOut` | Server did not respond in time | Retry once, then show error |
| `.cancelled` | Task was cancelled | No action needed; do not show error |
| `.cannotFindHost` | DNS failure | Check URL, show error |
| `.secureConnectionFailed` | TLS handshake failed | Check cert pinning, ATS config |
| `.userAuthenticationRequired` | 401 from proxy | Trigger auth flow |

### Decoding Server Error Bodies

```swift
struct APIErrorResponse: Decodable, Sendable {
    let code: String
    let message: String
}

func decodeAPIError(from data: Data) -> APIErrorResponse? {
    try? JSONDecoder().decode(APIErrorResponse.self, from: data)
}

// Usage in catch block
catch NetworkError.httpError(let statusCode, let data) {
    if let apiError = decodeAPIError(from: data) {
        showError("Server error: \(apiError.message)")
    } else {
        showError("HTTP \(statusCode)")
    }
}
```

### Retry with Exponential Backoff

Use structured concurrency for retries. Respect task cancellation between
attempts. Skip retries for cancellation and 4xx client errors (except 429).

```swift
func withRetry<T: Sendable>(
    maxAttempts: Int = 3,
    initialDelay: Duration = .seconds(1),
    operation: @Sendable () async throws -> T
) async throws -> T {
    var lastError: Error?
    for attempt in 0..<maxAttempts {
        do {
            return try await operation()
        } catch {
            lastError = error
            if error is CancellationError { throw error }
            if case NetworkError.httpError(let code, _) = error,
               (400..<500).contains(code), code != 429 { throw error }
            if attempt < maxAttempts - 1 {
                try await Task.sleep(for: initialDelay * Int(pow(2.0, Double(attempt))))
            }
        }
    }
    throw lastError!
}
```

## Pagination

Build cursor-based or offset-based pagination with `AsyncSequence`.
Always check `Task.isCancelled` between pages. See
`references/urlsession-patterns.md` for complete `CursorPaginator` and
offset-based implementations.

## Network Reachability

Use `NWPathMonitor` from the Network framework — not third-party
Reachability libraries. Wrap in `AsyncStream` for structured concurrency.

```swift
import Network

func networkStatusStream() -> AsyncStream<NWPath.Status> {
    AsyncStream { continuation in
        let monitor = NWPathMonitor()
        monitor.pathUpdateHandler = { continuation.yield($0.status) }
        continuation.onTermination = { _ in monitor.cancel() }
        monitor.start(queue: DispatchQueue(label: "NetworkMonitor"))
    }
}
```

Check `path.isExpensive` (cellular) and `path.isConstrained` (Low Data
Mode) to adapt behavior (reduce image quality, skip prefetching).

## Configuring URLSession

Create a configured session for production code. `URLSession.shared` is
acceptable only for simple, one-off requests.

```swift
let configuration = URLSessionConfiguration.default
configuration.timeoutIntervalForRequest = 30
configuration.timeoutIntervalForResource = 300
configuration.waitsForConnectivity = true
configuration.requestCachePolicy = .returnCacheDataElseLoad
configuration.httpAdditionalHeaders = [
    "Accept": "application/json",
    "Accept-Language": Locale.preferredLanguages.first ?? "en"
]

let session = URLSession(configuration: configuration)
```

`waitsForConnectivity = true` is valuable -- it makes the session wait for
a network path instead of failing immediately when offline. Combine with
`urlSession(_:taskIsWaitingForConnectivity:)` delegate callback for UI
feedback.

## Common Mistakes

**DON'T:** Use `URLSession.shared` with custom configuration needs.
**DO:** Create a configured `URLSession` with appropriate timeouts, caching,
and delegate for production code.

**DON'T:** Force-unwrap `URL(string:)` with dynamic input.
**DO:** Use `URL(string:)` with proper error handling. Force-unwrap is
acceptable only for compile-time-constant strings.

**DON'T:** Decode JSON on the main thread for large payloads.
**DO:** Keep decoding on the calling context of the URLSession call, which
is off-main by default. Only hop to `@MainActor` to update UI state.

**DON'T:** Ignore cancellation in long-running network tasks.
**DO:** Check `Task.isCancelled` or call `try Task.checkCancellation()` in
loops (pagination, streaming, retry). Use `.task` in SwiftUI for automatic
cancellation.

**DON'T:** Use Alamofire or Moya when URLSession async/await handles the
need.
**DO:** Use URLSession directly. With async/await, the ergonomic gap that
justified third-party libraries no longer exists. Reserve third-party
libraries for genuinely missing features (e.g., image caching).

**DON'T:** Mock URLSession directly in tests.
**DO:** Use `URLProtocol` subclass for transport-level mocking, or use
protocol-based clients that accept a test double.

**DON'T:** Use `data(for:)` for large file downloads.
**DO:** Use `download(for:)` which streams to disk and avoids memory spikes.

**DON'T:** Fire network requests from `body` or view initializers.
**DO:** Use `.task` or `.task(id:)` to trigger network calls.

**DON'T:** Hardcode authentication tokens in requests.
**DO:** Inject tokens via middleware so they are centralized and refreshable.

**DON'T:** Ignore HTTP status codes and decode blindly.
**DO:** Validate status codes before decoding. A 200 with invalid JSON and
a 500 with an error body require different handling.

## Review Checklist

- [ ] All network calls use async/await (not completion handlers)
- [ ] Error handling covers URLError cases (.notConnectedToInternet, .timedOut, .cancelled)
- [ ] Requests are cancellable (respect Task cancellation via `.task` modifier or stored Task references)
- [ ] Authentication tokens injected via middleware, not hardcoded
- [ ] Response HTTP status codes validated before decoding
- [ ] Large downloads use `download(for:)` not `data(for:)`
- [ ] Network calls happen off `@MainActor` (only UI updates on main)
- [ ] URLSession configured with appropriate timeouts and caching
- [ ] Retry logic excludes cancellation and 4xx client errors
- [ ] Pagination checks `Task.isCancelled` between pages
- [ ] Sensitive tokens stored in Keychain (not UserDefaults or plain files)
- [ ] No force-unwrapped URLs from dynamic input
- [ ] Server error responses decoded and surfaced to users
- [ ] Ensure network response model types conform to Sendable; use @MainActor for UI-updating completion paths

## Reference Material

- See `references/urlsession-patterns.md` for complete API client
  implementation, multipart uploads, download progress, URLProtocol
  mocking, retry/backoff, certificate pinning, request logging, and
  pagination implementations.
- See `references/background-websocket.md` for background URLSession
  configuration, background downloads/uploads, WebSocket patterns with
  structured concurrency, and reconnection strategies.
- See `references/lightweight-clients.md` for the lightweight closure-based
  client pattern (struct of async closures, injected via init for testability
  and preview support).
