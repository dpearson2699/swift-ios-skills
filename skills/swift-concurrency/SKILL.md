---
name: swift-concurrency
description: "Resolve Swift concurrency compiler errors, adopt Swift 6.2 approachable concurrency (SE-0466), and write data-race-safe async code. Use when fixing Sendable conformance errors, actor isolation warnings, or strict concurrency diagnostics; when adopting default MainActor isolation, @concurrent, nonisolated(nonsending), or Task.immediate; when designing actor-based architectures, structured concurrency with TaskGroup, or background work offloading; or when migrating from @preconcurrency to full Swift 6 strict concurrency."
---

# Swift 6.2 Concurrency

Review, fix, and write concurrent Swift code targeting Swift 6.2+. Apply actor
isolation, Sendable safety, and modern concurrency patterns with minimal
behavior changes.

## Triage Workflow

When diagnosing a concurrency issue, follow this sequence:

### Step 1: Capture context

- Copy the exact compiler diagnostic(s) and the offending symbol(s).
- Identify the project's concurrency settings:
  - Swift language version (must be 6.2+).
  - Whether approachable concurrency (default MainActor isolation) is enabled.
  - Strict concurrency checking level (Complete / Targeted / Minimal).
- Determine the current actor context of the code (`@MainActor`, custom `actor`,
  `nonisolated`) and whether a default isolation mode is active.
- Confirm whether the code is UI-bound or intended to run off the main actor.

### Step 2: Apply the smallest safe fix

Prefer edits that preserve existing behavior while satisfying data-race safety.

| Situation | Recommended fix |
|---|---|
| UI-bound type | Annotate the type or relevant members with `@MainActor`. |
| Protocol conformance on MainActor type | Use an isolated conformance: `extension Foo: @MainActor Proto`. |
| Global / static state | Protect with `@MainActor` or move into an actor. |
| Background work needed | Use a `@concurrent` async function on a `nonisolated` type. |
| Sendable error | Prefer immutable value types. Add `Sendable` only when correct. |
| Cross-isolation callback | Use `sending` parameters (SE-0430) for finer control. |

### Step 3: Verify

- Rebuild and confirm the diagnostic is resolved.
- Check for new warnings introduced by the fix.
- Ensure no unnecessary `@unchecked Sendable` or `nonisolated(unsafe)` was added.

## Swift 6.2 Language Changes

Swift 6.2 introduces "approachable concurrency" -- a set of language changes
that make concurrent code safer by default while reducing annotation burden.

### SE-0466: Default MainActor Isolation

With the `-default-isolation MainActor` compiler flag (or the Xcode 26
"Approachable Concurrency" build setting), all code in a module runs on
`@MainActor` by default unless explicitly opted out.

**Effect:** Eliminates most data-race safety errors for UI-bound code and
global/static state without writing `@MainActor` everywhere.

```swift
// With default MainActor isolation enabled, these are implicitly @MainActor:
final class StickerLibrary {
    static let shared = StickerLibrary()  // safe -- on MainActor
    var stickers: [Sticker] = []
}

final class StickerModel {
    let photoProcessor = PhotoProcessor()
    var selection: [PhotosPickerItem] = []
}

// Conformances are also implicitly isolated:
extension StickerModel: Exportable {
    func export() {
        photoProcessor.exportAsPNG()
    }
}
```

**When to use:** Recommended for apps, scripts, and other executable targets
where most code is UI-bound. Not recommended for library targets that should
remain actor-agnostic.

### SE-0461: nonisolated(nonsending)

Nonisolated async functions now stay on the caller's actor by default instead
of hopping to the global concurrent executor. This is the
`nonisolated(nonsending)` behavior.

```swift
class PhotoProcessor {
    func extractSticker(data: Data, with id: String?) async -> Sticker? {
        // In Swift 6.2, this runs on the caller's actor (e.g., MainActor)
        // instead of hopping to a background thread.
        // ...
    }
}

@MainActor
final class StickerModel {
    let photoProcessor = PhotoProcessor()

    func extractSticker(_ item: PhotosPickerItem) async throws -> Sticker? {
        guard let data = try await item.loadTransferable(type: Data.self) else {
            return nil
        }
        // No data race -- photoProcessor stays on MainActor
        return await photoProcessor.extractSticker(data: data, with: item.itemIdentifier)
    }
}
```

Use `@concurrent` to explicitly request background execution when needed.

### @concurrent Attribute

`@concurrent` ensures a function always runs on the concurrent thread pool,
freeing the calling actor to run other tasks.

```swift
class PhotoProcessor {
    var cachedStickers: [String: Sticker] = [:]

    func extractSticker(data: Data, with id: String) async -> Sticker {
        if let sticker = cachedStickers[id] { return sticker }

        let sticker = await Self.extractSubject(from: data)
        cachedStickers[id] = sticker
        return sticker
    }

    @concurrent
    static func extractSubject(from data: Data) async -> Sticker {
        // Expensive image processing -- runs on background thread pool
        // ...
    }
}
```

To move a function to a background thread:
1. Ensure the containing type is `nonisolated` (or the function itself is).
2. Add `@concurrent` to the function.
3. Add `async` if not already asynchronous.
4. Add `await` at call sites.

```swift
nonisolated struct PhotoProcessor {
    @concurrent
    func process(data: Data) async -> ProcessedPhoto? { /* ... */ }
}

// Caller:
processedPhotos[item.id] = await PhotoProcessor().process(data: data)
```

### SE-0472: Task.immediate

`Task.immediate` starts executing synchronously on the current actor before
any suspension point, rather than being enqueued.

```swift
Task.immediate { await handleUserInput() }
```

Use for latency-sensitive work that should begin without delay. There is also
`Task.immediateDetached` which combines immediate start with detached semantics.

### SE-0475: Transactional Observation (Observations)

`Observations { }` provides async observation of `@Observable` types via
`AsyncSequence`, enabling transactional change tracking.

```swift
for await _ in Observations(tracking: { model.count }) {
    print("Count changed to \(model.count)")
}
```

### SE-0481: weak let

Immutable weak references (`weak let`) that enable `Sendable` conformance for
types holding weak references.

### Isolated Conformances

A conformance that needs MainActor state is called an *isolated conformance*.
The compiler ensures it is only used in a matching isolation context.

```swift
protocol Exportable {
    func export()
}

// Isolated conformance: only usable on MainActor
extension StickerModel: @MainActor Exportable {
    func export() {
        photoProcessor.exportAsPNG()
    }
}

@MainActor
struct ImageExporter {
    var items: [any Exportable]

    mutating func add(_ item: StickerModel) {
        items.append(item)  // OK -- ImageExporter is on MainActor
    }
}
```

If `ImageExporter` were `nonisolated`, adding a `StickerModel` would fail:
"Main actor-isolated conformance of 'StickerModel' to 'Exportable' cannot be
used in nonisolated context."

## Actor Isolation Rules

1. All mutable shared state MUST be protected by an actor or global actor.
2. `@MainActor` for all UI-touching code. No exceptions.
3. Use `nonisolated` only for methods that access immutable (`let`) properties
   or are pure computations.
4. Use `@concurrent` to explicitly move work off the caller's actor.
5. Never use `nonisolated(unsafe)` unless you have proven internal
   synchronization and exhausted all other options.
6. Never add manual locks (`NSLock`, `DispatchSemaphore`) inside actors.

## Sendable Rules

1. Value types (structs, enums) are automatically `Sendable` when all stored
   properties are `Sendable`.
2. Actors are implicitly `Sendable`.
3. `@MainActor` classes are implicitly `Sendable`. Do NOT add redundant
   `Sendable` conformance.
4. Non-actor classes: must be `final` with all stored properties `let` and
   `Sendable`.
5. `@unchecked Sendable` is a last resort. Document why the compiler cannot
   prove safety.
6. Use `sending` parameters (SE-0430) for finer-grained isolation control.
7. Use `@preconcurrency import` only for third-party libraries you cannot
   modify. Plan to remove it.

## Structured Concurrency Patterns

**Task:** Unstructured, inherits caller context.
```swift
Task { await doWork() }
```

**Task.detached:** No inherited context. Use only when you explicitly need to
break isolation inheritance.

**Task.immediate:** Starts immediately on current actor. Use for
latency-sensitive work.
```swift
Task.immediate { await handleUserInput() }
```

**async let:** Fixed number of concurrent operations.
```swift
async let a = fetchA()
async let b = fetchB()
let result = try await (a, b)
```

**TaskGroup:** Dynamic number of concurrent operations.
```swift
try await withThrowingTaskGroup(of: Item.self) { group in
    for id in ids {
        group.addTask { try await fetch(id) }
    }
    for try await item in group { process(item) }
}
```

## Task Cancellation

- Cancellation is cooperative. Check `Task.isCancelled` or call
  `try Task.checkCancellation()` in loops.
- Use `.task` modifier in SwiftUI -- it handles cancellation on view disappear.
- Use `withTaskCancellationHandler` for cleanup.
- Cancel stored tasks in `deinit` or `onDisappear`.

## Actor Reentrancy

Actors are reentrant. State can change across suspension points.

```swift
// WRONG: State may change during await
actor Counter {
    var count = 0
    func increment() async {
        let current = count
        await someWork()
        count = current + 1  // BUG: count may have changed
    }
}

// CORRECT: Mutate synchronously, no reentrancy risk
actor Counter {
    var count = 0
    func increment() { count += 1 }
}
```

## AsyncSequence and AsyncStream

Use `AsyncStream` to bridge callback/delegate APIs:

```swift
let stream = AsyncStream<Location> { continuation in
    let delegate = LocationDelegate { location in
        continuation.yield(location)
    }
    continuation.onTermination = { _ in delegate.stop() }
    delegate.start()
}
```

Use `withCheckedContinuation` / `withCheckedThrowingContinuation` for
single-value callbacks. Resume exactly once.

## @Observable and Concurrency

- `@Observable` classes should be `@MainActor` for view models.
- Use `@State` to own an `@Observable` instance (replaces `@StateObject`).
- Use `Observations { }` (SE-0475) for async observation of `@Observable`
  properties as an `AsyncSequence`.

## Common Mistakes

1. **Blocking the main actor.** Heavy computation on `@MainActor` freezes UI.
   Move to a `@concurrent` function.
2. **Unnecessary @MainActor.** Network layers, data processing, and model code
   do not need `@MainActor`. Only UI-touching code does.
3. **Actors for stateless code.** No mutable state means no actor needed. Use a
   plain struct or function.
4. **Actors for immutable data.** Use a `Sendable` struct, not an actor.
5. **Task.detached without good reason.** Loses priority, task-local values,
   and cancellation propagation.
6. **Forgetting task cancellation.** Store `Task` references and cancel them, or
   use the `.task` view modifier.
7. **Retain cycles in Tasks.** Use `[weak self]` when capturing `self` in
   long-lived stored tasks.
8. **Semaphores in async context.** `DispatchSemaphore.wait()` in async code
   will deadlock. Use structured concurrency instead.
9. **Split isolation.** Mixing `@MainActor` and `nonisolated` properties in one
   type. Isolate the entire type consistently.
10. **MainActor.run instead of static isolation.** Prefer `@MainActor func`
    over `await MainActor.run { }`.

## Review Checklist

- [ ] All mutable shared state is actor-isolated
- [ ] No data races (no unprotected cross-isolation access)
- [ ] Tasks are cancelled when no longer needed
- [ ] No blocking calls on `@MainActor`
- [ ] No manual locks inside actors
- [ ] `Sendable` conformance is correct (no unjustified `@unchecked`)
- [ ] Actor reentrancy is handled (no state assumptions across awaits)
- [ ] `@preconcurrency` imports are documented with removal plan
- [ ] Heavy work uses `@concurrent`, not `@MainActor`
- [ ] `.task` modifier used in SwiftUI instead of manual Task management

## Reference Material

- See `references/swift-6-2-concurrency.md` for detailed Swift 6.2 changes,
  patterns, and migration examples.
- See `references/approachable-concurrency.md` for the approachable concurrency
  mode quick-reference guide.
- See `references/swiftui-concurrency.md` for SwiftUI-specific concurrency
  guidance.

