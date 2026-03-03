# URLSession Patterns Reference

Complete implementation patterns for URLSession-based networking. Each
section is self-contained with production-ready code.

---

## Complete API Client with Protocol

A full-featured client with middleware support, configurable decoding,
and response validation.

### Protocol

```swift
protocol APIClientProtocol: Sendable {
    func request<T: Decodable & Sendable>(
        _ type: T.Type,
        endpoint: Endpoint
    ) async throws -> T

    func request(endpoint: Endpoint) async throws

    func upload<T: Decodable & Sendable>(
        _ type: T.Type,
        endpoint: Endpoint,
        body: Data
    ) async throws -> T
}
```

### Endpoint Definition

```swift
struct Endpoint: Sendable {
    let path: String
    var method: HTTPMethod = .get
    var queryItems: [URLQueryItem] = []
    var headers: [String: String] = [:]
    var body: Data? = nil
    var cachePolicy: URLRequest.CachePolicy = .useProtocolCachePolicy
    var timeoutInterval: TimeInterval = 30

    enum HTTPMethod: String, Sendable {
        case get = "GET"
        case post = "POST"
        case put = "PUT"
        case patch = "PATCH"
        case delete = "DELETE"
    }

    func urlRequest(relativeTo baseURL: URL) -> URLRequest {
        var components = URLComponents(
            url: baseURL.appendingPathComponent(path),
            resolvingAgainstBaseURL: true
        )!
        if !queryItems.isEmpty {
            components.queryItems = queryItems
        }
        var request = URLRequest(url: components.url!)
        request.httpMethod = method.rawValue
        request.httpBody = body
        request.cachePolicy = cachePolicy
        request.timeoutInterval = timeoutInterval
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }
        return request
    }
}
```

### Client Implementation

```swift
final class APIClient: APIClientProtocol {
    private let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    private let middlewares: [any RequestMiddleware]

    init(
        baseURL: URL,
        session: URLSession = .shared,
        decoder: JSONDecoder = {
            let d = JSONDecoder()
            d.dateDecodingStrategy = .iso8601
            d.keyDecodingStrategy = .convertFromSnakeCase
            return d
        }(),
        encoder: JSONEncoder = {
            let e = JSONEncoder()
            e.dateEncodingStrategy = .iso8601
            e.keyEncodingStrategy = .convertToSnakeCase
            return e
        }(),
        middlewares: [any RequestMiddleware] = []
    ) {
        self.baseURL = baseURL
        self.session = session
        self.decoder = decoder
        self.encoder = encoder
        self.middlewares = middlewares
    }

    func request<T: Decodable & Sendable>(
        _ type: T.Type,
        endpoint: Endpoint
    ) async throws -> T {
        let request = try await prepareRequest(for: endpoint)
        let (data, response) = try await session.data(for: request)
        try validateResponse(response, data: data)
        return try decoder.decode(T.self, from: data)
    }

    func request(endpoint: Endpoint) async throws {
        let request = try await prepareRequest(for: endpoint)
        let (data, response) = try await session.data(for: request)
        try validateResponse(response, data: data)
    }

    func upload<T: Decodable & Sendable>(
        _ type: T.Type,
        endpoint: Endpoint,
        body: Data
    ) async throws -> T {
        var request = try await prepareRequest(for: endpoint)
        request.httpBody = body
        let (data, response) = try await session.upload(for: request, from: body)
        try validateResponse(response, data: data)
        return try decoder.decode(T.self, from: data)
    }

    // MARK: - Convenience methods

    func get<T: Decodable & Sendable>(
        _ type: T.Type,
        path: String,
        queryItems: [URLQueryItem] = []
    ) async throws -> T {
        try await request(type, endpoint: Endpoint(
            path: path,
            method: .get,
            queryItems: queryItems
        ))
    }

    func post<T: Decodable & Sendable, B: Encodable & Sendable>(
        _ type: T.Type,
        path: String,
        body: B
    ) async throws -> T {
        let bodyData = try encoder.encode(body)
        return try await request(type, endpoint: Endpoint(
            path: path,
            method: .post,
            headers: ["Content-Type": "application/json"],
            body: bodyData
        ))
    }

    func delete(path: String) async throws {
        try await request(endpoint: Endpoint(path: path, method: .delete))
    }

    // MARK: - Internal

    private func prepareRequest(for endpoint: Endpoint) async throws -> URLRequest {
        var request = endpoint.urlRequest(relativeTo: baseURL)
        for middleware in middlewares {
            request = try await middleware.prepare(request)
        }
        return request
    }

    private func validateResponse(_ response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            let apiError = try? decoder.decode(APIErrorBody.self, from: data)
            throw NetworkError.httpError(
                statusCode: http.statusCode,
                data: data,
                message: apiError?.message
            )
        }
    }
}
```

### Error Types

```swift
enum NetworkError: Error, Sendable, LocalizedError {
    case invalidResponse
    case httpError(statusCode: Int, data: Data, message: String? = nil)
    case noConnection
    case timedOut
    case cancelled

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid server response"
        case .httpError(let code, _, let message):
            return message ?? "HTTP error \(code)"
        case .noConnection:
            return "No internet connection"
        case .timedOut:
            return "Request timed out"
        case .cancelled:
            return nil
        }
    }

    static func from(_ urlError: URLError) -> NetworkError {
        switch urlError.code {
        case .notConnectedToInternet, .networkConnectionLost:
            return .noConnection
        case .timedOut:
            return .timedOut
        case .cancelled:
            return .cancelled
        default:
            return .invalidResponse
        }
    }
}

struct APIErrorBody: Decodable, Sendable {
    let code: String?
    let message: String?
}
```

---

## Request Builder Pattern

For complex request construction, a builder provides a fluent API that
reduces errors.

```swift
struct RequestBuilder: Sendable {
    private var method: String = "GET"
    private var path: String
    private var baseURL: URL
    private var queryItems: [URLQueryItem] = []
    private var headers: [String: String] = [:]
    private var body: Data?
    private var cachePolicy: URLRequest.CachePolicy = .useProtocolCachePolicy
    private var timeout: TimeInterval = 30

    init(baseURL: URL, path: String) {
        self.baseURL = baseURL
        self.path = path
    }

    func method(_ method: String) -> RequestBuilder {
        var copy = self
        copy.method = method
        return copy
    }

    func query(_ name: String, _ value: String?) -> RequestBuilder {
        guard let value else { return self }
        var copy = self
        copy.queryItems.append(URLQueryItem(name: name, value: value))
        return copy
    }

    func header(_ name: String, _ value: String) -> RequestBuilder {
        var copy = self
        copy.headers[name] = value
        return copy
    }

    func jsonBody<T: Encodable>(_ value: T) throws -> RequestBuilder {
        var copy = self
        copy.body = try JSONEncoder().encode(value)
        copy.headers["Content-Type"] = "application/json"
        return copy
    }

    func timeout(_ interval: TimeInterval) -> RequestBuilder {
        var copy = self
        copy.timeout = interval
        return copy
    }

    func cachePolicy(_ policy: URLRequest.CachePolicy) -> RequestBuilder {
        var copy = self
        copy.cachePolicy = policy
        return copy
    }

    func build() -> URLRequest {
        var components = URLComponents(
            url: baseURL.appendingPathComponent(path),
            resolvingAgainstBaseURL: true
        )!
        if !queryItems.isEmpty {
            components.queryItems = queryItems
        }
        var request = URLRequest(url: components.url!)
        request.httpMethod = method
        request.httpBody = body
        request.cachePolicy = cachePolicy
        request.timeoutInterval = timeout
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }
        return request
    }
}

// Usage
let request = try RequestBuilder(baseURL: apiURL, path: "users")
    .method("POST")
    .header("X-Request-ID", UUID().uuidString)
    .jsonBody(CreateUserRequest(name: "Alice", email: "alice@example.com"))
    .timeout(15)
    .build()
```

---

## Multipart Form Upload

Multipart/form-data uploads are common for file attachments. Build the
body manually -- no third-party library needed.

```swift
struct MultipartFormData: Sendable {
    private let boundary: String
    private var parts: [Part] = []

    init(boundary: String = UUID().uuidString) {
        self.boundary = boundary
    }

    var contentType: String {
        "multipart/form-data; boundary=\(boundary)"
    }

    mutating func addField(name: String, value: String) {
        parts.append(Part(
            headers: "Content-Disposition: form-data; name=\"\(name)\"",
            body: Data(value.utf8)
        ))
    }

    mutating func addFile(
        name: String,
        filename: String,
        mimeType: String,
        data: Data
    ) {
        parts.append(Part(
            headers: """
            Content-Disposition: form-data; name="\(name)"; filename="\(filename)"\r
            Content-Type: \(mimeType)
            """,
            body: data
        ))
    }

    func encode() -> Data {
        var data = Data()
        let crlf = "\r\n"
        for part in parts {
            data.append("--\(boundary)\(crlf)")
            data.append("\(part.headers)\(crlf)\(crlf)")
            data.append(part.body)
            data.append(crlf)
        }
        data.append("--\(boundary)--\(crlf)")
        return data
    }

    private struct Part: Sendable {
        let headers: String
        let body: Data
    }
}

extension Data {
    mutating func append(_ string: String) {
        append(Data(string.utf8))
    }
}

// Usage
var form = MultipartFormData()
form.addField(name: "title", value: "Profile Photo")
form.addFile(
    name: "image",
    filename: "photo.jpg",
    mimeType: "image/jpeg",
    data: imageData
)

var request = URLRequest(url: uploadURL)
request.httpMethod = "POST"
request.setValue(form.contentType, forHTTPHeaderField: "Content-Type")
request.httpBody = form.encode()

let (data, response) = try await URLSession.shared.upload(
    for: request,
    from: form.encode()
)
```

---

## Download with Progress Tracking

Use `bytes(for:)` for real-time progress. The response includes
`expectedContentLength` for calculating percentage.

```swift
@available(iOS 15.0, *)
func downloadWithProgress(
    from url: URL,
    progressHandler: @Sendable (Double) -> Void
) async throws -> Data {
    let (bytes, response) = try await URLSession.shared.bytes(from: url)

    let expectedLength = response.expectedContentLength
    var receivedData = Data()
    if expectedLength > 0 {
        receivedData.reserveCapacity(Int(expectedLength))
    }

    var receivedLength: Int64 = 0
    for try await byte in bytes {
        receivedData.append(byte)
        receivedLength += 1
        if expectedLength > 0 {
            let progress = Double(receivedLength) / Double(expectedLength)
            progressHandler(progress)
        }
    }

    return receivedData
}
```

For large files, prefer `URLSessionDownloadTask` with a delegate for
better memory efficiency and background support. See
`references/background-websocket.md`.

### Download to File with Progress (Delegate-Based)

```swift
@available(iOS 15.0, *)
final class DownloadManager: NSObject, URLSessionDownloadDelegate, Sendable {
    private let continuation: AsyncStream<DownloadEvent>.Continuation

    enum DownloadEvent: Sendable {
        case progress(Double)
        case completed(URL)
        case failed(Error)
    }

    static func download(from url: URL) -> AsyncStream<DownloadEvent> {
        AsyncStream { continuation in
            let manager = DownloadManager(continuation: continuation)
            let session = URLSession(
                configuration: .default,
                delegate: manager,
                delegateQueue: nil
            )
            session.downloadTask(with: url).resume()
        }
    }

    private init(continuation: AsyncStream<DownloadEvent>.Continuation) {
        self.continuation = continuation
    }

    nonisolated func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didFinishDownloadingTo location: URL
    ) {
        // Move file to permanent location before this method returns
        let destination = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        do {
            try FileManager.default.moveItem(at: location, to: destination)
            continuation.yield(.completed(destination))
        } catch {
            continuation.yield(.failed(error))
        }
        continuation.finish()
    }

    nonisolated func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didWriteData bytesWritten: Int64,
        totalBytesWritten: Int64,
        totalBytesExpectedToWrite: Int64
    ) {
        guard totalBytesExpectedToWrite > 0 else { return }
        let progress = Double(totalBytesWritten) / Double(totalBytesExpectedToWrite)
        continuation.yield(.progress(progress))
    }

    nonisolated func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didCompleteWithError error: (any Error)?
    ) {
        if let error {
            continuation.yield(.failed(error))
            continuation.finish()
        }
    }
}
```

---

## Cursor-Based Pagination

A reusable paginator that conforms to `AsyncSequence`, yielding pages
of results until the server indicates no more data.

```swift
struct PageResponse<T: Decodable & Sendable>: Decodable, Sendable {
    let data: [T]
    let pagination: PaginationInfo
}

struct PaginationInfo: Decodable, Sendable {
    let nextCursor: String?
    let hasMore: Bool
}

struct CursorPaginator<T: Decodable & Sendable>: AsyncSequence {
    typealias Element = [T]

    private let fetchPage: @Sendable (String?) async throws -> PageResponse<T>

    init(fetchPage: @escaping @Sendable (String?) async throws -> PageResponse<T>) {
        self.fetchPage = fetchPage
    }

    func makeAsyncIterator() -> Iterator {
        Iterator(fetchPage: fetchPage)
    }

    struct Iterator: AsyncIteratorProtocol {
        private let fetchPage: @Sendable (String?) async throws -> PageResponse<T>
        private var cursor: String?
        private var exhausted = false

        init(fetchPage: @escaping @Sendable (String?) async throws -> PageResponse<T>) {
            self.fetchPage = fetchPage
        }

        mutating func next() async throws -> [T]? {
            guard !exhausted else { return nil }
            try Task.checkCancellation()

            let response = try await fetchPage(cursor)
            cursor = response.pagination.nextCursor
            exhausted = !response.pagination.hasMore

            return response.data.isEmpty ? nil : response.data
        }
    }
}

// Usage
let paginator = CursorPaginator<User> { cursor in
    var queryItems = [URLQueryItem(name: "limit", value: "50")]
    if let cursor {
        queryItems.append(URLQueryItem(name: "cursor", value: cursor))
    }
    return try await client.get(
        PageResponse<User>.self,
        path: "users",
        queryItems: queryItems
    )
}

var allUsers: [User] = []
for try await batch in paginator {
    allUsers.append(contentsOf: batch)
}
```

---

## Offset-Based Pagination

```swift
struct OffsetPaginator<T: Decodable & Sendable>: AsyncSequence {
    typealias Element = [T]

    private let pageSize: Int
    private let fetchPage: @Sendable (Int, Int) async throws -> [T]

    init(
        pageSize: Int = 20,
        fetchPage: @escaping @Sendable (_ offset: Int, _ limit: Int) async throws -> [T]
    ) {
        self.pageSize = pageSize
        self.fetchPage = fetchPage
    }

    func makeAsyncIterator() -> Iterator {
        Iterator(pageSize: pageSize, fetchPage: fetchPage)
    }

    struct Iterator: AsyncIteratorProtocol {
        private let pageSize: Int
        private let fetchPage: @Sendable (Int, Int) async throws -> [T]
        private var offset = 0
        private var exhausted = false

        init(
            pageSize: Int,
            fetchPage: @escaping @Sendable (Int, Int) async throws -> [T]
        ) {
            self.pageSize = pageSize
            self.fetchPage = fetchPage
        }

        mutating func next() async throws -> [T]? {
            guard !exhausted else { return nil }
            try Task.checkCancellation()

            let items = try await fetchPage(offset, pageSize)
            offset += items.count
            if items.count < pageSize { exhausted = true }

            return items.isEmpty ? nil : items
        }
    }
}
```

---

## URLProtocol Mock for Testing

`URLProtocol` is the correct way to mock network responses at the
transport level. It works with any URLSession configuration and does
not require changing production code.

```swift
final class MockURLProtocol: URLProtocol {
    nonisolated(unsafe) static var requestHandler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool { true }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        guard let handler = Self.requestHandler else {
            fatalError("MockURLProtocol.requestHandler is not set")
        }

        do {
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}
```

### Test Setup

```swift
import Testing

@Suite struct APIClientTests {
    let client: APIClient
    let session: URLSession

    init() {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [MockURLProtocol.self]
        session = URLSession(configuration: config)
        client = APIClient(
            baseURL: URL(string: "https://api.example.com")!,
            session: session
        )
    }

    @Test func fetchUsersDecodesCorrectly() async throws {
        let usersJSON = """
        [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        """
        MockURLProtocol.requestHandler = { request in
            #expect(request.url?.path == "/users")
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (response, Data(usersJSON.utf8))
        }

        let users: [User] = try await client.get([User].self, path: "users")
        #expect(users.count == 2)
        #expect(users[0].name == "Alice")
    }

    @Test func fetchReturnsHTTPError() async throws {
        MockURLProtocol.requestHandler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 404,
                httpVersion: nil,
                headerFields: nil
            )!
            return (response, Data())
        }

        await #expect(throws: NetworkError.self) {
            let _: [User] = try await client.get([User].self, path: "missing")
        }
    }

    @Test func requestIncludesAuthHeader() async throws {
        let authClient = APIClient(
            baseURL: URL(string: "https://api.example.com")!,
            session: session,
            middlewares: [AuthMiddleware { "test-token" }]
        )

        MockURLProtocol.requestHandler = { request in
            #expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer test-token")
            let response = HTTPURLResponse(
                url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil
            )!
            return (response, Data("{}".utf8))
        }

        let _: EmptyResponse = try await authClient.get(EmptyResponse.self, path: "me")
    }
}

struct EmptyResponse: Decodable, Sendable {}
```

---

## Retry with Exponential Backoff

Respect cancellation. Do not retry client errors (4xx except 429 rate
limiting). Include jitter to prevent thundering herd.

```swift
func withRetry<T: Sendable>(
    maxAttempts: Int = 3,
    initialDelay: Duration = .seconds(1),
    maxDelay: Duration = .seconds(30),
    shouldRetry: @Sendable (Error) -> Bool = { error in
        if error is CancellationError { return false }
        if case NetworkError.httpError(let code, _, _) = error {
            return code >= 500 || code == 429
        }
        if let urlError = error as? URLError {
            return [.timedOut, .networkConnectionLost, .notConnectedToInternet]
                .contains(urlError.code)
        }
        return false
    },
    operation: @Sendable () async throws -> T
) async throws -> T {
    var lastError: Error?

    for attempt in 0..<maxAttempts {
        try Task.checkCancellation()
        do {
            return try await operation()
        } catch {
            lastError = error
            guard shouldRetry(error), attempt < maxAttempts - 1 else {
                throw error
            }
            // Exponential backoff with jitter
            let base = Double(initialDelay.components.seconds) * pow(2.0, Double(attempt))
            let capped = min(base, Double(maxDelay.components.seconds))
            let jitter = Double.random(in: 0...(capped * 0.1))
            let delay = Duration.seconds(capped + jitter)
            try await Task.sleep(for: delay)
        }
    }

    throw lastError!
}

// Usage
let users = try await withRetry {
    try await client.get([User].self, path: "users")
}
```

---

## Certificate Pinning (URLSessionDelegate)

Pin the server's public key hash rather than the certificate itself.
Certificates rotate; public keys are more stable. Always include a
backup pin.

```swift
import CryptoKit

final class PinningDelegate: NSObject, URLSessionDelegate, Sendable {
    /// SHA-256 hashes of Subject Public Key Info (SPKI) in base64
    private let pinnedKeyHashes: Set<String>

    init(pinnedKeyHashes: Set<String>) {
        self.pinnedKeyHashes = pinnedKeyHashes
    }

    nonisolated func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge
    ) async -> (URLSession.AuthChallengeDisposition, URLCredential?) {
        guard challenge.protectionSpace.authenticationMethod
                == NSURLAuthenticationMethodServerTrust,
              let trust = challenge.protectionSpace.serverTrust else {
            return (.performDefaultHandling, nil)
        }

        // Evaluate the trust chain
        var error: CFError?
        guard SecTrustEvaluateWithError(trust, &error) else {
            return (.cancelAuthenticationChallenge, nil)
        }

        // Extract the leaf certificate's public key
        guard let chain = SecTrustCopyCertificateChain(trust) as? [SecCertificate],
              let leafCert = chain.first,
              let publicKey = SecCertificateCopyKey(leafCert),
              let publicKeyData = SecKeyCopyExternalRepresentation(
                  publicKey, nil
              ) as Data? else {
            return (.cancelAuthenticationChallenge, nil)
        }

        let keyHash = SHA256.hash(data: publicKeyData)
        let hashString = Data(keyHash).base64EncodedString()

        if pinnedKeyHashes.contains(hashString) {
            return (.useCredential, URLCredential(trust: trust))
        }

        return (.cancelAuthenticationChallenge, nil)
    }
}

// Usage
let delegate = PinningDelegate(pinnedKeyHashes: [
    "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=",  // Primary
    "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=",  // Backup
])

let session = URLSession(
    configuration: .default,
    delegate: delegate,
    delegateQueue: nil
)
```

**Important considerations:**
- Pin at least two keys (primary + backup) to avoid lockout during rotation.
- Have a remote kill switch (feature flag) to disable pinning in emergencies.
- Test certificate rotation in staging before deploying to production.
- Do not pin intermediate CA certificates -- they rotate more frequently.

---

## Request Logging / Debugging Middleware

Log outgoing requests and incoming responses for debugging. Disable or
reduce verbosity in release builds.

```swift
struct LoggingMiddleware: RequestMiddleware {
    let logger: Logger

    func prepare(_ request: URLRequest) async throws -> URLRequest {
        #if DEBUG
        let method = request.httpMethod ?? "GET"
        let url = request.url?.absoluteString ?? "unknown"
        logger.debug("[\(method)] \(url)")
        if let headers = request.allHTTPHeaderFields {
            for (key, value) in headers where key != "Authorization" {
                logger.debug("  \(key): \(value)")
            }
        }
        if let body = request.httpBody, body.count < 10_000 {
            logger.debug("  Body: \(String(data: body, encoding: .utf8) ?? "<binary>")")
        }
        #endif
        return request
    }
}
```

### Response Logging

To log responses, wrap the transport call rather than using middleware:

```swift
func loggedRequest<T: Decodable & Sendable>(
    _ type: T.Type,
    endpoint: Endpoint,
    logger: Logger
) async throws -> T {
    let start = ContinuousClock().now
    do {
        let result: T = try await request(type, endpoint: endpoint)
        let elapsed = ContinuousClock().now - start
        logger.debug("[\(endpoint.method.rawValue)] \(endpoint.path) -> 200 (\(elapsed))")
        return result
    } catch {
        let elapsed = ContinuousClock().now - start
        logger.error("[\(endpoint.method.rawValue)] \(endpoint.path) -> ERROR (\(elapsed)): \(error)")
        throw error
    }
}
```

---

## Request Caching Strategies

### URLCache Configuration

```swift
// 50 MB memory / 200 MB disk cache
let cache = URLCache(
    memoryCapacity: 50 * 1024 * 1024,
    diskCapacity: 200 * 1024 * 1024,
    directory: FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)
        .first?.appendingPathComponent("URLCache")
)

let config = URLSessionConfiguration.default
config.urlCache = cache
config.requestCachePolicy = .returnCacheDataElseLoad

let session = URLSession(configuration: config)
```

### Per-Request Cache Control

```swift
// Force fresh data
var request = URLRequest(url: url)
request.cachePolicy = .reloadIgnoringLocalCacheData

// Use cached if available
request.cachePolicy = .returnCacheDataElseLoad

// Cache only (offline mode)
request.cachePolicy = .returnCacheDataDontLoad
```

### ETag / If-None-Match

```swift
func fetchWithETag<T: Decodable & Sendable>(
    _ type: T.Type,
    url: URL,
    cachedETag: String?,
    cachedData: Data?
) async throws -> (T, String?) {
    var request = URLRequest(url: url)
    if let etag = cachedETag {
        request.setValue(etag, forHTTPHeaderField: "If-None-Match")
    }

    let (data, response) = try await URLSession.shared.data(for: request)
    guard let http = response as? HTTPURLResponse else {
        throw NetworkError.invalidResponse
    }

    if http.statusCode == 304, let cachedData {
        // Not modified -- use cached data
        let decoded = try JSONDecoder().decode(T.self, from: cachedData)
        return (decoded, cachedETag)
    }

    let newETag = http.value(forHTTPHeaderField: "ETag")
    let decoded = try JSONDecoder().decode(T.self, from: data)
    return (decoded, newETag)
}
```

---

## Server-Sent Events (SSE) Parsing

Use `bytes(for:)` to consume a streaming SSE endpoint.

```swift
struct ServerSentEvent: Sendable {
    var event: String?
    var data: String
    var id: String?
}

func sseStream(from url: URL) -> AsyncThrowingStream<ServerSentEvent, Error> {
    AsyncThrowingStream { continuation in
        let task = Task {
            do {
                var request = URLRequest(url: url)
                request.setValue("text/event-stream", forHTTPHeaderField: "Accept")

                let (bytes, _) = try await URLSession.shared.bytes(for: request)

                var currentEvent: String?
                var currentData = ""
                var currentId: String?

                for try await line in bytes.lines {
                    if line.isEmpty {
                        // Empty line = dispatch event
                        if !currentData.isEmpty {
                            continuation.yield(ServerSentEvent(
                                event: currentEvent,
                                data: currentData.trimmingCharacters(in: .newlines),
                                id: currentId
                            ))
                        }
                        currentEvent = nil
                        currentData = ""
                        currentId = nil
                    } else if line.hasPrefix("event:") {
                        currentEvent = String(line.dropFirst(6)).trimmingCharacters(in: .whitespaces)
                    } else if line.hasPrefix("data:") {
                        let value = String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces)
                        currentData += currentData.isEmpty ? value : "\n" + value
                    } else if line.hasPrefix("id:") {
                        currentId = String(line.dropFirst(3)).trimmingCharacters(in: .whitespaces)
                    }
                }
                continuation.finish()
            } catch {
                continuation.finish(throwing: error)
            }
        }
        continuation.onTermination = { _ in task.cancel() }
    }
}
```

---

## Configured URLSession for Production

```swift
enum SessionFactory {
    static func makeDefault(delegate: (any URLSessionDelegate)? = nil) -> URLSession {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 300
        config.waitsForConnectivity = true
        config.httpMaximumConnectionsPerHost = 6
        config.requestCachePolicy = .useProtocolCachePolicy
        config.httpAdditionalHeaders = [
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
        ]

        let cache = URLCache(
            memoryCapacity: 25 * 1024 * 1024,
            diskCapacity: 100 * 1024 * 1024
        )
        config.urlCache = cache

        return URLSession(
            configuration: config,
            delegate: delegate,
            delegateQueue: nil
        )
    }
}
```
