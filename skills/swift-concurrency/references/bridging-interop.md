# Bridging and Interop

Patterns for bridging callback-based, delegate-based, and GCD code into Swift Concurrency.

## Contents

- [Checked Continuations](#checked-continuations)
- [AsyncStream from Callbacks](#asyncstream-from-callbacks)
- [GCD Migration](#gcd-migration)

## Checked Continuations

Use `withCheckedContinuation` (non-throwing) or `withCheckedThrowingContinuation` (throwing) to bridge completion-handler APIs into async/await. Available iOS 13+.

Docs: [withCheckedContinuation](https://sosumi.ai/documentation/swift/withcheckedcontinuation(isolation:function:_:)) · [withCheckedThrowingContinuation](https://sosumi.ai/documentation/swift/withcheckedthrowingcontinuation(isolation:function:_:))

### Basic Pattern

```swift
func fetchData() async throws -> Data {
    try await withCheckedThrowingContinuation { continuation in
        legacyFetch { result in
            switch result {
            case .success(let data):
                continuation.resume(returning: data)
            case .failure(let error):
                continuation.resume(throwing: error)
            }
        }
    }
}
```

### Rules

- **Resume exactly once.** Missing resume suspends the task forever (leak). Double resume crashes at runtime.
- **Prefer checked over unsafe.** `withCheckedContinuation` detects misuse at runtime with diagnostics. Use `withUnsafeContinuation` only in performance-critical paths after correctness is proven.
- **Capture continuation carefully.** The continuation escapes the closure — ensure all code paths resume it, including error and cancellation paths.

### Delegate Bridging

```swift
class LocationBridge: NSObject, CLLocationManagerDelegate {
    private var continuation: CheckedContinuation<CLLocation, any Error>?
    private let manager = CLLocationManager()

    func requestLocation() async throws -> CLLocation {
        try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
            manager.delegate = self
            manager.requestLocation()
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        continuation?.resume(returning: locations[0])
        continuation = nil
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        continuation?.resume(throwing: error)
        continuation = nil
    }
}
```

### Cancellation Support

```swift
func fetchWithCancellation() async throws -> Data {
    try await withTaskCancellationHandler {
        try await withCheckedThrowingContinuation { continuation in
            let task = legacyFetch { result in
                switch result {
                case .success(let data): continuation.resume(returning: data)
                case .failure(let error): continuation.resume(throwing: error)
                }
            }
            // Store task for cancellation
        }
    } onCancel: {
        // Cancel the underlying work
    }
}
```

## AsyncStream from Callbacks

For APIs that deliver multiple values over time (delegates, NotificationCenter), use `AsyncStream`:

```swift
func locationUpdates() -> AsyncStream<CLLocation> {
    AsyncStream { continuation in
        let delegate = StreamingLocationDelegate(continuation: continuation)
        continuation.onTermination = { _ in
            delegate.stop()
        }
        delegate.start()
    }
}
```

## GCD Migration

| GCD Pattern | Swift Concurrency Replacement |
| --- | --- |
| `DispatchQueue.main.async { }` | `@MainActor` isolation or `MainActor.run { }` |
| `DispatchQueue.global().async { }` | `Task { }` or `Task.detached { }` (Swift 6.2: `@concurrent`) |
| `DispatchGroup` | `async let` or `TaskGroup` |
| `DispatchSemaphore` | Actor isolation or `AsyncStream` |
| `DispatchWorkItem` with cancel | `Task` with `task.cancel()` |
| `DispatchQueue` serial queue | `actor` |
| `DispatchQueue.concurrentPerform` (async orchestration) | `withTaskGroup` |
| `DispatchQueue.concurrentPerform` (synchronous CPU-bound parallel-for, disjoint writes) | **Keep `concurrentPerform`** -- `TaskGroup` is not a replacement (Swift core team); see SKILL.md Mistake #11 / Actor Rule #5 carve-out |
| `DispatchSource.makeTimerSource` | `Task.sleep(for:)` in a loop, or `Clock` |

### DispatchGroup → TaskGroup

```swift
// Before (GCD)
let group = DispatchGroup()
for url in urls {
    group.enter()
    fetch(url) { _ in group.leave() }
}
group.notify(queue: .main) { updateUI() }

// After (Swift Concurrency)
let results = await withTaskGroup(of: Data?.self) { group in
    for url in urls {
        group.addTask { try? await fetch(url) }
    }
    return await group.reduce(into: [Data]()) { if let d = $1 { $0.append(d) } }
}
updateUI(results)
```

### Serial Queue → Actor

```swift
// Before
let serialQueue = DispatchQueue(label: "com.app.cache")
serialQueue.async { self.cache[key] = value }

// After
actor Cache {
    private var storage: [String: Data] = [:]
    func set(_ key: String, _ value: Data) { storage[key] = value }
    func get(_ key: String) -> Data? { storage[key] }
}
```
