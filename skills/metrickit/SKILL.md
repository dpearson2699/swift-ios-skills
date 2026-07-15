---
name: metrickit
description: Use when collecting or analyzing production iOS or iPadOS performance telemetry with MetricKit, including iOS 27 MetricManager async metric or diagnostic reports, hang or crash triage, custom signposts, extended launch measurement, durable export, or iOS 26 MXMetricManager compatibility.
---

# MetricKit

Use MetricKit for low-overhead production telemetry that complements local Instruments and Xcode Organizer analysis. On iOS and iPadOS 27, prefer the Swift-first `MetricManager` report sequences. Keep `MXMetricManager` only in an explicit iOS 26 compatibility branch.

> **Beta-sensitive:** The iOS/iPadOS 27 surface below is based on Apple's current beta documentation. It has not been locally compiler-verified because Xcode 27 is unavailable in this environment. Re-check the linked Apple documentation and compile with the shipping Xcode 27 SDK before release.

Load [MetricKit Extended and Compatibility Patterns](references/metrickit-patterns.md) when implementing durable ingestion, detailed report analysis, or the iOS 26 compatibility path.

## Contents

- [MetricManager Setup](#metricmanager-setup)
- [Receiving Metric Reports](#receiving-metric-reports)
- [Receiving Diagnostic Reports](#receiving-diagnostic-reports)
- [Key Metric Results](#key-metric-results)
- [Call Stack Trees](#call-stack-trees)
- [Custom Signpost Metrics](#custom-signpost-metrics)
- [Durable Export and Upload](#durable-export-and-upload)
- [Extended Launch Measurement](#extended-launch-measurement)
- [iOS 26 Compatibility](#ios-26-compatibility)
- [Xcode Organizer](#xcode-organizer)
- [Scope Boundaries](#scope-boundaries)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## MetricManager Setup

At app launch, create and retain one long-lived `MetricManager`. Start exactly one consumer task for `metricReports` and one for `diagnosticReports`.

Both properties expose nonthrowing `AsyncSequence` values:

- `metricReports: some AsyncSequence<MetricReport, Never>`
- `diagnosticReports: some AsyncSequence<DiagnosticReport, Never>`

Apple documents that concurrent consumers of one sequence can receive nondeterministic subsets. Fan out only after the single consumer receives and durably stores a report; delayed subscription can miss reports.

```swift
import MetricKit

@available(iOS 27.0, *)
final class MetricsService {
    private let manager = MetricManager()
    private var metricTask: Task<Void, Never>?
    private var diagnosticTask: Task<Void, Never>?

    func start(
        persistMetric: @escaping @Sendable (MetricReport) async -> Void,
        persistDiagnostic: @escaping @Sendable (DiagnosticReport) async -> Void
    ) {
        guard metricTask == nil, diagnosticTask == nil else { return }
        let manager = manager

        metricTask = Task {
            for await report in manager.metricReports {
                await persistMetric(report)
            }
        }

        diagnosticTask = Task {
            for await report in manager.diagnosticReports {
                await persistDiagnostic(report)
            }
        }
    }

    deinit {
        metricTask?.cancel()
        diagnosticTask?.cancel()
    }
}
```

The persistence closures are application-specific. Implement them with the durable-first workflow below rather than dropping, logging only, or directly uploading each report. If state-scoped metrics are needed, construct the manager with the documented `init(enabledStateReportingDomains:)` initializer and the required domains.

## Receiving Metric Reports

`MetricReport` is `Codable` and `Sendable`. It describes an interval through:

- `timeRange: DateInterval`
- optional `environment` metadata
- `intervalEntries` for full-day and shorter interval measurements
- `stateEntries` for measurements associated with application states

Metric reports normally arrive on a daily cadence. Persist the complete report before extracting individual results.

For daily analysis, read the documented `fullDayEntry` and switch over its `MetricResult` values:

```swift
let entry = report.intervalEntries.fullDayEntry

for result in entry.values {
    switch result {
    case .hangTime(let metric):
        analyzeHangTime(metric)
    case .peakMemory(let metric):
        analyzePeakMemory(metric)
    case .timeToFirstDraw(let metric):
        analyzeLaunch(metric)
    case .signpostInterval(let metric):
        analyzeSignpost(metric)
    @unknown default:
        preserveUnknownMetric(result)
    }
}
```

Use `@unknown default` so a beta or future result does not make the ingestion pipeline brittle. Preserve the raw encoded report even when the current app does not understand a result.

## Receiving Diagnostic Reports

`DiagnosticReport` is `Codable` and `Sendable`. It contains a `timeRange`, required `environment` metadata, and one `DiagnosticResult`.

Diagnostics are individual, event-based reports intended for prompt delivery when MetricKit produces them. Do not assume every crash, hang, or resource event generates a report; system sampling and eligibility still apply.

After durable storage, route the result explicitly:

```swift
switch report.result {
case .crash(let diagnostic):
    analyzeCrash(diagnostic)
case .hang(let diagnostic):
    analyzeHang(diagnostic)
case .cpuException(let diagnostic):
    analyzeCPUException(diagnostic)
case .diskWriteException(let diagnostic):
    analyzeDiskWrites(diagnostic)
case .appLaunch(let diagnostic):
    analyzeLaunch(diagnostic)
case .memoryException(let diagnostic):
    analyzeMemory(diagnostic)
@unknown default:
    preserveUnknownDiagnostic(report)
}
```

The iOS/iPadOS 27 diagnostic types are `CrashDiagnostic`, `HangDiagnostic`, `CPUExceptionDiagnostic`, `DiskWriteExceptionDiagnostic`, `AppLaunchDiagnostic`, and `MemoryExceptionDiagnostic`. The memory-exception case is new in iOS 27.

Useful fields include:

| Diagnostic | Important fields |
|---|---|
| `CrashDiagnostic` | `callStackTree`, exception type/code/reason, signal, virtual-memory region, termination category/reason |
| `HangDiagnostic` | `callStackTree`, `hangDuration` |
| `CPUExceptionDiagnostic` | `callStackTree`, `totalCPUTime`, `totalSampledTime` |
| `DiskWriteExceptionDiagnostic` | `callStackTree`, `totalBytesWritten` |
| `AppLaunchDiagnostic` | `callStackTree`, `launchDuration` |
| `MemoryExceptionDiagnostic` | `callStackTree` |

## Key Metric Results

Choose a small telemetry vocabulary that matches the investigation rather than exporting every result. Prioritize the relevant categories: responsiveness and terminations; runtime, CPU, memory, network, and storage; or launch, display/GPU, and custom intervals.

Aggregate by app version and environment metadata, compare distributions rather than single values, and correlate regressions with releases. Avoid treating a daily aggregate as a precise trace of one user action.

Load the [Key Metric Result Catalog](references/metrickit-patterns.md#key-metric-result-catalog) when mapping exact `MetricResult` cases into a parser or dashboard.

## Call Stack Trees

The iOS 27 `CallStackTree` replaces `MXCallStackTree`. It is `Codable` and `Sendable` and exposes:

- `forEachFrame` for frame traversal
- `callStackThreads` for thread-oriented analysis
- `binaryInfo` for image and binary metadata

Store the complete diagnostic report before flattening or symbolication. Preserve binary identifiers and offsets so server-side symbolication can use matching archives and dSYMs.

## Custom Signpost Metrics

Create an OS log through the manager, then use `mxSignpost` for begin/end measurement:

```swift
let log = manager.logHandle(category: "ImagePipeline")

mxSignpost(.begin, log: log, name: "Decode")
await decodeImage()
mxSignpost(.end, log: log, name: "Decode")
```

MetricKit exposes the aggregate as `MetricResult.signpostInterval`. Do not search for a `signpostMetrics` array on `MetricReport`.

Use `mxSignpost` when MetricKit resource measurement is required. Apple documents that intervals created with `OSSignposter` and a MetricKit log handle do not populate the resource-measurement fields that `mxSignpost` provides.

Keep high-volume local tracing separate from the small set of stable production intervals used for MetricKit aggregation.

## Durable Export and Upload

Treat report delivery as an at-least-once ingestion problem:

1. Encode the complete `MetricReport` or `DiagnosticReport` with `JSONEncoder`.
2. Atomically enqueue the bytes in an app-owned durable outbox.
3. Record report type, schema version, app version, and a stable deduplication key.
4. Acknowledge local processing only after the enqueue succeeds.
5. Upload later with retry, backoff, batching, and retention limits.
6. Mark the outbox item uploaded only after the server accepts it.

```swift
let data = try JSONEncoder().encode(report)
try await durableOutbox.enqueue(data, kind: .metric)
```

`durableOutbox` is an application-owned abstraction, not a MetricKit API. Do not perform a synchronous network upload inside the sequence consumer.

Durable local storage is the recovery mechanism for reports received through the modern sequences; do not make successful ingestion depend on an assumed modern backfill API.

## Extended Launch Measurement

Use `trackLaunchTask(id:onTrackingError:_:)` on the manager for work that extends beyond time to first draw:

```swift
await manager.trackLaunchTask(
    id: "bootstrap-data",
    onTrackingError: { error in
        recordLaunchTrackingError(error)
    }
) {
    await bootstrapApplication()
}
```

The API is `@MainActor` and has synchronous and asynchronous overloads. The task closure's result and thrown error propagate to the caller; a `MetricManager.LaunchTaskError` is reported through `onTrackingError` without interrupting the tracked work. Results appear as `MetricResult.extendedLaunch`.

Use stable `LaunchTaskID` values and track only launch-critical work.

## iOS 26 Compatibility

For an app that still deploys to iOS 26, use an availability boundary:

- iOS/iPadOS 27: use `MetricManager` and consume both async report sequences.
- iOS/iPadOS 26 and earlier supported releases: use `MXMetricManager.shared`, an `MXMetricManagerSubscriber`, and the legacy payload callbacks.

The legacy APIs remain the only documented branch with `pastPayloads` and `pastDiagnosticPayloads`. `MXMetricManager` is deprecated in iOS 27, so isolate it behind availability checks rather than mixing legacy payloads into the modern pipeline.

Load [iOS 26 Compatibility](references/metrickit-patterns.md#ios-26-compatibility) for the full subscriber, legacy signpost, past-payload, and extended-launch patterns.

## Xcode Organizer

Use Xcode Organizer to inspect Apple-aggregated production metrics, hangs, crashes, and regressions before building a custom backend. Use direct MetricKit ingestion when the product needs custom correlation, retention, alerting, or integration with an existing observability system.

Do not expect development-device runs to reproduce the population, cadence, or aggregation of production reports.

## Scope Boundaries

| Task | Use instead |
|---|---|
| Reproduce a problem locally or record a detailed trace | `debugging-instruments` |
| Diagnose retained objects or memory graph paths | `ios-memgraph-analysis` |
| Tune SwiftUI invalidation, identity, or scrolling code | `swiftui-performance` |
| Study structured EnergyKit impact data | `energykit` |
| Design general logging and os_signpost strategy | `swift-logging` |

MetricKit identifies production symptoms and trends. Route the actual code fix to the skill that owns the affected subsystem.

## Common Mistakes

| Mistake | Correction |
|---|---|
| Uploading directly in the sequence loop | Encode and enqueue locally first; upload asynchronously later. |
| Assuming every diagnostic event produces a report | Treat diagnostics as sampled, system-produced evidence. |
| Looking for `pastPayloads` on `MetricManager` | Keep legacy backfill only in the iOS 26 `MXMetricManager` branch. |
| Parsing only known enum cases | Preserve the raw report and use `@unknown default`. |
| Using `MXMetricManager.makeLogHandle` in the iOS 27 branch | Use `manager.logHandle(category:)`. |
| Using paired extend/finish launch calls in the iOS 27 branch | Use `trackLaunchTask`. |
| Treating MetricKit aggregates as local traces | Reproduce with Instruments and signposts. |

## Review Checklist

- [ ] The iOS 27 branch starts at launch with one retained `MetricManager` and one consumer per report sequence.
- [ ] Every report is encoded and durably enqueued before analysis or upload.
- [ ] Diagnostic and metric switches use `@unknown default`.
- [ ] Unknown raw reports remain recoverable.
- [ ] Symbolication metadata and matching dSYMs are retained.
- [ ] Custom intervals use `manager.logHandle(category:)` and `mxSignpost`.
- [ ] Extended launch work uses `trackLaunchTask`.
- [ ] The iOS 26 `MXMetricManager` path is isolated behind availability checks.
- [ ] Production aggregates lead to a local Instruments investigation when appropriate.
- [ ] iOS 27 beta APIs have been rechecked and compiled with the shipping Xcode 27 SDK.

## References

- [MetricManager](https://sosumi.ai/documentation/metrickit/metricmanager)
- [Metric report sequence](https://sosumi.ai/documentation/metrickit/metricmanager/metricreports)
- [Diagnostic report sequence](https://sosumi.ai/documentation/metrickit/metricmanager/diagnosticreports)
- [MetricReport](https://sosumi.ai/documentation/metrickit/metricreport)
- [DiagnosticReport](https://sosumi.ai/documentation/metrickit/diagnosticreport)
- [MetricResult](https://sosumi.ai/documentation/metrickit/metricresult)
- [DiagnosticResult](https://sosumi.ai/documentation/metrickit/diagnosticresult)
- [CallStackTree](https://sosumi.ai/documentation/metrickit/callstacktree)
- [Monitoring app performance with MetricKit](https://sosumi.ai/documentation/metrickit/monitoring-app-performance-with-metrickit)
- [Analyzing app performance with MetricKit](https://sosumi.ai/documentation/metrickit/analyzing-app-performance-with-metrickit)
- [iOS & iPadOS 27 release notes](https://sosumi.ai/documentation/ios-ipados-release-notes/ios-ipados-27-release-notes)
- [What's new in MetricKit (WWDC26)](https://sosumi.ai/videos/play/wwdc2026/222)
- [MetricKit Extended and Compatibility Patterns](references/metrickit-patterns.md)
