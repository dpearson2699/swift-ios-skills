---
name: swiftui-performance
description: Audit and improve SwiftUI runtime performance. Use for slow rendering, janky scrolling, high CPU, memory usage, excessive view updates, layout thrash, body evaluation cost, identity churn, view lifetime issues, lazy loading, Instruments profiling guidance, and performance audit requests.
---

# SwiftUI Performance

## Overview

Audit SwiftUI view performance end-to-end, from instrumentation and baselining to root-cause analysis and concrete remediation steps.

## Workflow Decision Tree

- If the user provides code, start with "Code-First Review."
- If the user only describes symptoms, ask for minimal code/context, then do "Code-First Review."
- If code review is inconclusive, go to "Guide the User to Profile" and ask for a trace or screenshots.

## 1. Code-First Review

Collect:
- Target view/feature code.
- Data flow: state, environment, observable models.
- Symptoms and reproduction steps.

Focus on:
- View invalidation storms from broad state changes.
- Unstable identity in lists (`id` churn, `UUID()` per render).
- Top-level conditional view swapping (`if/else` returning different root branches).
- Heavy work in `body` (formatting, sorting, image decoding).
- Layout thrash (deep stacks, `GeometryReader`, preference chains).
- Large images without downsampling or resizing.
- Over-animated hierarchies (implicit animations on large trees).

Provide:
- Likely root causes with code references.
- Suggested fixes and refactors.
- If needed, a minimal repro or instrumentation suggestion.

## 2. Guide the User to Profile

Explain how to collect data with Instruments:
- Use the SwiftUI template in Instruments (always profile a **Release build**).
- Reproduce the exact interaction (scroll, navigation, animation).
- Capture SwiftUI timeline and Time Profiler.
- Export or screenshot the relevant lanes and the call tree.

Ask for:
- Trace export or screenshots of SwiftUI lanes + Time Profiler call tree.
- Device/OS/build configuration.

## 3. Analyze and Diagnose

Prioritize likely SwiftUI culprits:
- View invalidation storms from broad state changes.
- Unstable identity in lists (`id` churn, `UUID()` per render).
- Top-level conditional view swapping (`if/else` returning different root branches).
- Heavy work in `body` (formatting, sorting, image decoding).
- Layout thrash (deep stacks, `GeometryReader`, preference chains).
- Large images without downsampling or resizing.
- Over-animated hierarchies (implicit animations on large trees).

Summarize findings with evidence from traces/logs.

## 4. Remediate

Apply targeted fixes:
- Narrow state scope (`@State`/`@Observable` closer to leaf views).
- Stabilize identities for `ForEach` and lists.
- Move heavy work out of `body` (precompute, cache, `@State`).
- Use `equatable()` or value wrappers for expensive subtrees.
- Downsample images before rendering.
- Reduce layout complexity or use fixed sizing where possible.

## Common Code Smells (and Fixes)

Look for these patterns during code review.

### Expensive formatters in `body`

```swift
var body: some View {
    let number = NumberFormatter() // slow allocation
    let measure = MeasurementFormatter() // slow allocation
    Text(measure.string(from: .init(value: meters, unit: .meters)))
}
```

Prefer cached formatters in a model or a dedicated helper:

```swift
final class DistanceFormatter {
    static let shared = DistanceFormatter()
    let number = NumberFormatter()
    let measure = MeasurementFormatter()
}
```

### Computed properties that do heavy work

```swift
var filtered: [Item] {
    items.filter { $0.isEnabled } // runs on every body eval
}
```

Prefer precompute or cache on change:

```swift
@State private var filtered: [Item] = []
// update filtered when inputs change
```

### Sorting/filtering in `body` or `ForEach`

```swift
List {
    ForEach(items.sorted(by: sortRule)) { item in
        Row(item)
    }
}
```

Prefer sort once before view updates:

```swift
let sortedItems = items.sorted(by: sortRule)
```

### Inline filtering in `ForEach`

```swift
ForEach(items.filter { $0.isEnabled }) { item in
    Row(item)
}
```

Prefer a prefiltered collection with stable identity.

### Unstable identity

```swift
ForEach(items, id: \.self) { item in
    Row(item)
}
```

Avoid `id: \.self` for non-stable values; use a stable ID.

### Top-level conditional view swapping

```swift
var content: some View {
    if isEditing {
        editingView
    } else {
        readOnlyView
    }
}
```

Prefer one stable base view and localize conditions to sections/modifiers (for example inside `toolbar`, row content, `overlay`, or `disabled`). This reduces root identity churn and helps SwiftUI diffing stay efficient.

### Image decoding on the main thread

```swift
Image(uiImage: UIImage(data: data)!)
```

Prefer decode/downsample off the main thread and store the result.

### Broad dependencies in observable models

```swift
@Observable class Model {
    var items: [Item] = []
}

var body: some View {
    Row(isFavorite: model.items.contains(item))
}
```

Prefer granular view models or per-item state to reduce update fan-out.

## 5. Verify

Ask the user to re-run the same capture and compare with baseline metrics.
Summarize the delta (CPU, frame drops, memory peak) if provided.

## Outputs

Provide:
- A short metrics table (before/after if available).
- Top issues (ordered by impact).
- Proposed fixes with estimated effort.

## MCP Tool Notes

- **xcodebuildmcp**: When building for profiling, use Release configuration. Debug builds include extra runtime checks that distort performance measurements. Always profile Release builds on a real device when possible.

## Common Mistakes

1. **Profiling Debug builds.** Debug builds include extra runtime checks and disable optimizations, producing misleading perf data. Profile Release builds on a real device.
2. **Observing an entire model when only one property is needed.** Break large `@Observable` models into focused ones, or use computed properties/closures to narrow observation scope.
3. **Using `GeometryReader` inside ScrollView items.** GeometryReader forces eager sizing and defeats lazy loading. Prefer `.onGeometryChange` (iOS 18+) or measure outside the lazy container.
4. **Calling `DateFormatter()` or `NumberFormatter()` inside `body`.** These are expensive to create. Make them static or move them outside the view.
5. **Animating non-equatable state.** If SwiftUI cannot determine equality, it redraws every frame. Conform state to `Equatable` or use `.animation(_:value:)` with an explicit value.
6. **Large flat `List` without identifiers.** Use `id:` or make items `Identifiable` so SwiftUI can diff efficiently instead of rebuilding the entire list.
7. **Unnecessary `@State` wrapper objects.** Wrapping a simple value type in a class for `@State` defeats value semantics. Use plain `@State` with structs.
8. **Blocking `MainActor` with synchronous I/O.** File reads, JSON parsing of large payloads, and image decoding should happen off the main actor. Use `Task.detached` or a custom actor.

## Review Checklist

- [ ] No `DateFormatter`/`NumberFormatter` allocations inside `body`
- [ ] Large lists use `Identifiable` items or explicit `id:`
- [ ] `@Observable` models expose only the properties views actually read
- [ ] Heavy computation is off `MainActor` (image processing, parsing)
- [ ] `GeometryReader` is not inside a `LazyVStack`/`LazyHStack`/`List`
- [ ] Animations use explicit `value:` parameter
- [ ] No synchronous network/file I/O on the main thread
- [ ] Profiling done on Release build, real device
- [ ] `@Observable` view models are `@MainActor`-isolated; types crossing concurrency boundaries are `Sendable`

## References

- Demystify SwiftUI performance (WWDC23): `references/demystify-swiftui-performance-wwdc23.md`
- Optimizing SwiftUI performance with Instruments: `references/optimizing-swiftui-performance-instruments.md`
- Understanding hangs in your app: `references/understanding-hangs-in-your-app.md`
- Understanding and improving SwiftUI performance: `references/understanding-improving-swiftui-performance.md`
