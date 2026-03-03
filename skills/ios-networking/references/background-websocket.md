# Background Transfers and WebSocket

Patterns for background URLSession downloads/uploads and
URLSessionWebSocketTask with structured concurrency.

---

## Background URLSession Configuration

Background sessions allow transfers to continue when the app is
suspended or terminated. The system manages the transfer in a separate
process and wakes the app on completion.

### Why Background Sessions

- Downloads/uploads survive app suspension, termination, and device restarts.
- The system handles retries for network failures automatically.
- Required for any transfer the user expects to complete even if they
  switch away from the app (e.g., file sync, media downloads).

### Configuration

```swift
@available(iOS 15.0, *)
final class BackgroundDownloadManager: NSObject, Sendable {
    static let shared = BackgroundDownloadManager()

    /// Use a unique identifier tied to your app's bundle ID.
    /// The system uses this to reconnect to the session after relaunch.
    private let sessionID = "com.example.app.background-downloads"

    /// Lazy-initialized background session. Must use a delegate, not async/await,
    /// because the system delivers events through the delegate after app relaunch.
    lazy var session: URLSession = {
        let config = URLSessionConfiguration.background(
            withIdentifier: sessionID
        )
        config.isDiscretionary = false          // Start immediately (true = system-scheduled)
        config.sessionSendsLaunchEvents = true  // Wake app on completion
        config.allowsExpensiveNetworkAccess = true
        config.allowsConstrainedNetworkAccess = false  // Respect Low Data Mode
        config.timeoutIntervalForResource = 24 * 60 * 60  // 24 hours

        return URLSession(
            configuration: config,
            delegate: self,
            delegateQueue: nil  // Use a system-managed serial queue
        )
    }()

    /// Store completionHandler from AppDelegate for system callback
    nonisolated(unsafe) var backgroundCompletionHandler: (() -> Void)?
}
```

### Key Configuration Options

| Property | Effect |
|---|---|
| `isDiscretionary` | `true` = system schedules for optimal battery/network. Use for non-urgent sync. `false` = start immediately. |
| `sessionSendsLaunchEvents` | Relaunches the app when transfers complete. Required for completion handling. |
| `allowsConstrainedNetworkAccess` | `false` = honor Low Data Mode. Good for optional downloads. |
| `allowsExpensiveNetworkAccess` | `false` = Wi-Fi only. Use for large transfers. |
| `timeoutIntervalForResource` | Maximum time for the entire transfer. Default is 7 days. |

---

## Background Download Tasks

Background downloads must use `downloadTask(with:)`, not `data(for:)`.
The async/await overloads are not supported for background sessions --
you must use the delegate pattern.

```swift
extension BackgroundDownloadManager {
    func startDownload(from url: URL) -> URLSessionDownloadTask {
        let task = session.downloadTask(with: url)
        task.earliestBeginDate = Date()  // Start now
        task.countOfBytesClientExpectsToSend = 0
        task.countOfBytesClientExpectsToReceive = 50 * 1024 * 1024  // Estimated size
        task.resume()
        return task
    }

    func startDownload(from url: URL, resumeData: Data) -> URLSessionDownloadTask {
        let task = session.downloadTask(withResumeData: resumeData)
        task.resume()
        return task
    }
}
```

### Download Delegate

```swift
extension BackgroundDownloadManager: URLSessionDownloadDelegate {
    nonisolated func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didFinishDownloadingTo location: URL
    ) {
        // CRITICAL: Move the file before this method returns.
        // The temporary file is deleted immediately after.
        let destinationDir = FileManager.default.urls(
            for: .documentDirectory,
            in: .userDomainMask
        ).first!

        let filename = downloadTask.originalRequest?.url?.lastPathComponent ?? UUID().uuidString
        let destination = destinationDir.appendingPathComponent(filename)

        do {
            // Remove existing file if present
            if FileManager.default.fileExists(atPath: destination.path) {
                try FileManager.default.removeItem(at: destination)
            }
            try FileManager.default.moveItem(at: location, to: destination)
            // Notify the app (post notification, update state, etc.)
        } catch {
            // Handle file move failure
        }
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
        // Update progress UI (dispatch to main if needed)
    }

    nonisolated func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didCompleteWithError error: (any Error)?
    ) {
        guard let error else { return }  // Success handled in didFinishDownloadingTo

        // Check for resume data on failure
        let nsError = error as NSError
        if let resumeData = nsError.userInfo[NSURLSessionDownloadTaskResumeData] as? Data {
            // Store resumeData for retry
            saveResumeData(resumeData, for: task)
        }
    }

    private func saveResumeData(_ data: Data, for task: URLSessionTask) {
        // Persist resume data to disk for later retry
        let key = task.originalRequest?.url?.absoluteString ?? ""
        let path = FileManager.default.temporaryDirectory
            .appendingPathComponent("resume-\(key.hashValue)")
        try? data.write(to: path)
    }
}
```

---

## Handling Background Session Events

When the system completes a background transfer and the app is not
running, it relaunches the app and calls the `AppDelegate` method. You
must call the system's completion handler after processing all events.

### UIKit App Delegate

```swift
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        handleEventsForBackgroundURLSession identifier: String,
        completionHandler: @escaping () -> Void
    ) {
        // Store the completion handler. The BackgroundDownloadManager will
        // call it after processing all pending events.
        BackgroundDownloadManager.shared.backgroundCompletionHandler = completionHandler

        // Accessing .session triggers lazy initialization, which reconnects
        // to the background session and starts delivering delegate events.
        _ = BackgroundDownloadManager.shared.session
    }
}
```

### Session-Level Delegate

```swift
extension BackgroundDownloadManager: URLSessionDelegate {
    nonisolated func urlSessionDidFinishEvents(
        forBackgroundURLSession session: URLSession
    ) {
        // Called after ALL pending delegate events have been delivered.
        // Call the stored completion handler on the main thread.
        Task { @MainActor in
            backgroundCompletionHandler?()
            backgroundCompletionHandler = nil
        }
    }
}
```

### SwiftUI App with AppDelegate Adapter

```swift
@main
struct MyApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
```

**Important:** The completion handler must be called exactly once and
on the main thread. Failing to call it causes the system to take a
snapshot of the app in the wrong state and may waste background runtime.

---

## Background Upload Tasks

Background uploads require data from a file, not from memory.

```swift
extension BackgroundDownloadManager {
    func startUpload(
        to url: URL,
        fileURL: URL,
        method: String = "POST",
        headers: [String: String] = [:]
    ) -> URLSessionUploadTask {
        var request = URLRequest(url: url)
        request.httpMethod = method
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }

        let task = session.uploadTask(with: request, fromFile: fileURL)
        task.resume()
        return task
    }
}
```

### Upload Delegate Methods

```swift
extension BackgroundDownloadManager {
    nonisolated func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didSendBodyData bytesSent: Int64,
        totalBytesSent: Int64,
        totalBytesExpectedToSend: Int64
    ) {
        guard totalBytesExpectedToSend > 0 else { return }
        let progress = Double(totalBytesSent) / Double(totalBytesExpectedToSend)
        // Update progress UI
    }
}
```

**Constraints of background uploads:**
- Data must come from a file (`uploadTask(with:fromFile:)`).
- `uploadTask(with:from: Data)` is not supported in background sessions.
- Write multipart form data to a temporary file first, then upload.

---

## URLSessionWebSocketTask

`URLSessionWebSocketTask` provides native WebSocket support without
third-party libraries. Available since iOS 13.

### Basic Connection

```swift
@available(iOS 15.0, *)
final class WebSocketConnection: Sendable {
    private let task: URLSessionWebSocketTask

    init(url: URL, session: URLSession = .shared) {
        self.task = session.webSocketTask(with: url)
    }

    func connect() {
        task.resume()
    }

    func disconnect(reason: String? = nil) {
        task.cancel(with: .normalClosure, reason: reason?.data(using: .utf8))
    }

    func send(_ message: URLSessionWebSocketTask.Message) async throws {
        try await task.send(message)
    }

    func send(text: String) async throws {
        try await task.send(.string(text))
    }

    func send(data: Data) async throws {
        try await task.send(.data(data))
    }

    func receive() async throws -> URLSessionWebSocketTask.Message {
        try await task.receive()
    }
}
```

### WebSocket with Structured Concurrency

The key pattern: run a receive loop as an async task that yields
messages through an `AsyncStream`. This integrates naturally with
structured concurrency.

```swift
@available(iOS 15.0, *)
actor WebSocketManager {
    private var task: URLSessionWebSocketTask?
    private var receiveTask: Task<Void, Never>?
    private let session: URLSession
    private let url: URL

    enum Event: Sendable {
        case connected
        case text(String)
        case data(Data)
        case disconnected(URLSessionWebSocketTask.CloseCode, Data?)
        case error(Error)
    }

    init(url: URL, session: URLSession = .shared) {
        self.url = url
        self.session = session
    }

    /// Returns a stream of WebSocket events. Call `connect()` to start.
    func events() -> AsyncStream<Event> {
        AsyncStream { continuation in
            let wsTask = session.webSocketTask(with: url)
            self.task = wsTask

            wsTask.resume()
            continuation.yield(.connected)

            // Start the receive loop
            self.receiveTask = Task { [weak self] in
                await self?.receiveLoop(continuation: continuation)
            }

            continuation.onTermination = { _ in
                Task { [weak self] in
                    await self?.disconnect()
                }
            }
        }
    }

    private func receiveLoop(continuation: AsyncStream<Event>.Continuation) async {
        guard let task else { return }

        while !Task.isCancelled {
            do {
                let message = try await task.receive()
                switch message {
                case .string(let text):
                    continuation.yield(.text(text))
                case .data(let data):
                    continuation.yield(.data(data))
                @unknown default:
                    break
                }
            } catch {
                // The receive threw -- connection closed or failed
                let closeCode = task.closeCode
                let closeReason = task.closeReason
                if closeCode == .invalid {
                    // Unexpected disconnection
                    continuation.yield(.error(error))
                } else {
                    continuation.yield(.disconnected(closeCode, closeReason))
                }
                continuation.finish()
                return
            }
        }
    }

    func send(text: String) async throws {
        try await task?.send(.string(text))
    }

    func send(data: Data) async throws {
        try await task?.send(.data(data))
    }

    func disconnect() {
        receiveTask?.cancel()
        receiveTask = nil
        task?.cancel(with: .normalClosure, reason: nil)
        task = nil
    }

    /// Send periodic pings to keep the connection alive
    func startPinging(interval: Duration = .seconds(30)) {
        Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: interval)
                guard let self else { return }
                await self.ping()
            }
        }
    }

    private func ping() {
        task?.sendPing { error in
            if let error {
                // Connection may be dead
                print("Ping failed: \(error)")
            }
        }
    }
}
```

### Usage in SwiftUI

```swift
@MainActor
@Observable final class ChatStore {
    var messages: [ChatMessage] = []
    var connectionState: ConnectionState = .disconnected

    enum ConnectionState { case disconnected, connecting, connected }

    private let wsManager: WebSocketManager
    private var eventTask: Task<Void, Never>?

    init(url: URL) {
        self.wsManager = WebSocketManager(url: url)
    }

    func connect() async {
        connectionState = .connecting
        let stream = await wsManager.events()

        eventTask = Task {
            for await event in stream {
                await handleEvent(event)
            }
        }
    }

    func sendMessage(_ text: String) async {
        do {
            try await wsManager.send(text: text)
            messages.append(ChatMessage(text: text, isOutgoing: true))
        } catch {
            // Handle send failure
        }
    }

    func disconnect() async {
        eventTask?.cancel()
        eventTask = nil
        await wsManager.disconnect()
        connectionState = .disconnected
    }

    private func handleEvent(_ event: WebSocketManager.Event) async {
        switch event {
        case .connected:
            connectionState = .connected
        case .text(let text):
            messages.append(ChatMessage(text: text, isOutgoing: false))
        case .data(let data):
            if let text = String(data: data, encoding: .utf8) {
                messages.append(ChatMessage(text: text, isOutgoing: false))
            }
        case .disconnected:
            connectionState = .disconnected
        case .error:
            connectionState = .disconnected
            // Optionally trigger reconnection
        }
    }
}
```

```swift
struct ChatView: View {
    @State var store: ChatStore

    var body: some View {
        List(store.messages) { message in
            ChatBubble(message: message)
        }
        .task { await store.connect() }
        .onDisappear { Task { await store.disconnect() } }
    }
}
```

---

## WebSocket Reconnection Strategy

Network drops happen. A robust WebSocket client must reconnect
automatically with exponential backoff.

```swift
@available(iOS 15.0, *)
actor ReconnectingWebSocket {
    private let url: URL
    private let session: URLSession
    private let maxReconnectAttempts: Int
    private let initialDelay: Duration
    private let maxDelay: Duration

    private var currentManager: WebSocketManager?
    private var reconnectAttempts = 0
    private var isIntentionalDisconnect = false

    init(
        url: URL,
        session: URLSession = .shared,
        maxReconnectAttempts: Int = 10,
        initialDelay: Duration = .seconds(1),
        maxDelay: Duration = .seconds(60)
    ) {
        self.url = url
        self.session = session
        self.maxReconnectAttempts = maxReconnectAttempts
        self.initialDelay = initialDelay
        self.maxDelay = maxDelay
    }

    /// Returns a stream that automatically reconnects on disconnection.
    func events() -> AsyncStream<WebSocketManager.Event> {
        AsyncStream { continuation in
            Task {
                await connectWithReconnection(continuation: continuation)
            }
            continuation.onTermination = { _ in
                Task { [weak self] in
                    await self?.intentionalDisconnect()
                }
            }
        }
    }

    private func connectWithReconnection(
        continuation: AsyncStream<WebSocketManager.Event>.Continuation
    ) async {
        while !isIntentionalDisconnect && reconnectAttempts < maxReconnectAttempts {
            guard !Task.isCancelled else { break }

            let manager = WebSocketManager(url: url, session: session)
            currentManager = manager
            let stream = await manager.events()

            for await event in stream {
                switch event {
                case .connected:
                    reconnectAttempts = 0  // Reset on successful connection
                    continuation.yield(event)
                case .error, .disconnected:
                    continuation.yield(event)
                default:
                    continuation.yield(event)
                }
            }

            // Stream ended -- attempt reconnection unless intentional
            guard !isIntentionalDisconnect, !Task.isCancelled else { break }

            reconnectAttempts += 1
            let delay = calculateBackoff()
            do {
                try await Task.sleep(for: delay)
            } catch {
                break  // Cancelled during sleep
            }
        }

        continuation.finish()
    }

    private func calculateBackoff() -> Duration {
        let base = Double(initialDelay.components.seconds) * pow(2.0, Double(reconnectAttempts - 1))
        let capped = min(base, Double(maxDelay.components.seconds))
        let jitter = Double.random(in: 0...(capped * 0.25))
        return .seconds(capped + jitter)
    }

    func send(text: String) async throws {
        try await currentManager?.send(text: text)
    }

    func send(data: Data) async throws {
        try await currentManager?.send(data: data)
    }

    private func intentionalDisconnect() {
        isIntentionalDisconnect = true
        Task {
            await currentManager?.disconnect()
        }
    }
}
```

---

## WebSocket with Codable Messages

For typed message protocols (common in chat, gaming, real-time apps),
decode/encode messages automatically.

```swift
protocol WebSocketMessage: Codable, Sendable {
    static var messageType: String { get }
}

struct TypedWebSocketTransport {
    private let manager: WebSocketManager
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    init(manager: WebSocketManager) {
        self.manager = manager
    }

    func send<T: WebSocketMessage>(_ message: T) async throws {
        let envelope = MessageEnvelope(
            type: T.messageType,
            payload: try encoder.encode(message)
        )
        let data = try encoder.encode(envelope)
        try await manager.send(data: data)
    }

    /// Typed event stream that decodes known message types
    func typedEvents() async -> AsyncStream<DecodedEvent> {
        let rawEvents = await manager.events()
        return AsyncStream { continuation in
            Task {
                for await event in rawEvents {
                    switch event {
                    case .data(let data):
                        if let envelope = try? decoder.decode(MessageEnvelope.self, from: data) {
                            continuation.yield(.message(type: envelope.type, payload: envelope.payload))
                        }
                    case .text(let text):
                        if let data = text.data(using: .utf8),
                           let envelope = try? decoder.decode(MessageEnvelope.self, from: data) {
                            continuation.yield(.message(type: envelope.type, payload: envelope.payload))
                        }
                    case .connected:
                        continuation.yield(.connected)
                    case .disconnected(let code, _):
                        continuation.yield(.disconnected(code))
                    case .error(let error):
                        continuation.yield(.error(error))
                    }
                }
                continuation.finish()
            }
        }
    }

    enum DecodedEvent: Sendable {
        case connected
        case message(type: String, payload: Data)
        case disconnected(URLSessionWebSocketTask.CloseCode)
        case error(Error)
    }

    private struct MessageEnvelope: Codable, Sendable {
        let type: String
        let payload: Data
    }
}
```

---

## Background Session Gotchas

### The session identifier must be unique per app
If two sessions share the same identifier, events may be delivered to
the wrong delegate. Use your bundle identifier as a prefix.

### Background sessions do not support async/await overloads
The `data(for:)` and `download(for:)` async methods are not available
on background sessions. Use `downloadTask(with:)` and the delegate.

### Only download and upload tasks are supported
Data tasks (`dataTask`) are not supported in background sessions. Convert
data requests to download tasks if needed for background execution.

### The app may be terminated and relaunched
Store any state you need (task identifiers, file destinations) to disk.
Do not rely on in-memory state surviving a background relaunch.

### File must be moved in didFinishDownloadingTo
The temporary file at `location` is deleted as soon as the delegate
method returns. Always move or copy the file synchronously within the
callback.

### Call the system completion handler exactly once
Store the completion handler from
`application(_:handleEventsForBackgroundURLSession:completionHandler:)`
and invoke it in `urlSessionDidFinishEvents(forBackgroundURLSession:)`
on the main thread.

### Test on a real device
Background session behavior differs significantly between the Simulator
and real devices. Always test background transfers on hardware.

---

## Combining Background Downloads with SwiftUI Progress

Bridge the delegate-based background download to an `@Observable` model
for live UI updates.

```swift
@MainActor
@Observable final class DownloadTracker {
    var downloads: [URL: DownloadProgress] = [:]

    struct DownloadProgress: Sendable {
        var fractionCompleted: Double = 0
        var state: State = .downloading

        enum State: Sendable { case downloading, completed, failed }
    }

    func updateProgress(for url: URL, fraction: Double) {
        downloads[url, default: DownloadProgress()].fractionCompleted = fraction
    }

    func markCompleted(for url: URL) {
        downloads[url]?.state = .completed
        downloads[url]?.fractionCompleted = 1.0
    }

    func markFailed(for url: URL) {
        downloads[url]?.state = .failed
    }
}
```

Wire the delegate to the tracker:

```swift
extension BackgroundDownloadManager {
    // Called from delegate methods; dispatches to MainActor
    func reportProgress(for url: URL, fraction: Double) {
        Task { @MainActor in
            downloadTracker.updateProgress(for: url, fraction: fraction)
        }
    }
}
```

---

## WebSocket Authentication

WebSocket connections often require authentication via a token in the
initial handshake (either as a query parameter or a custom header).

```swift
func authenticatedWebSocket(
    baseURL: URL,
    token: String
) -> URLSessionWebSocketTask {
    // Option 1: Token as query parameter
    var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: true)!
    components.queryItems = [URLQueryItem(name: "token", value: token)]
    let task = URLSession.shared.webSocketTask(with: components.url!)

    // Option 2: Token as custom header (use URLRequest)
    var request = URLRequest(url: baseURL)
    request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    let taskWithHeader = URLSession.shared.webSocketTask(with: request)

    return taskWithHeader
}
```

**Prefer the header approach** when the server supports it. Query
parameters may appear in server access logs, which is a security
concern for tokens.

---

## WebSocket Subprotocol Negotiation

```swift
// Request a specific subprotocol (e.g., graphql-ws)
let task = URLSession.shared.webSocketTask(
    with: url,
    protocols: ["graphql-transport-ws"]
)
task.resume()

// After connection, verify the negotiated protocol
// via the URLSessionWebSocketDelegate
```

```swift
extension WebSocketConnection: URLSessionWebSocketDelegate {
    nonisolated func urlSession(
        _ session: URLSession,
        webSocketTask: URLSessionWebSocketTask,
        didOpenWithProtocol protocol: String?
    ) {
        print("Connected with protocol: \(`protocol` ?? "none")")
    }

    nonisolated func urlSession(
        _ session: URLSession,
        webSocketTask: URLSessionWebSocketTask,
        didCloseWith closeCode: URLSessionWebSocketTask.CloseCode,
        reason: Data?
    ) {
        let reasonString = reason.flatMap { String(data: $0, encoding: .utf8) }
        print("Closed: \(closeCode) - \(reasonString ?? "no reason")")
    }
}
```
