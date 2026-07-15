# MetricKit Extended and Compatibility Patterns

Use these patterns after choosing the iOS/iPadOS 27 `MetricManager` path or the isolated iOS 26 `MXMetricManager` compatibility path in the main skill.

> **Beta-sensitive:** The iOS/iPadOS 27 examples follow Apple's current beta documentation. They have not been locally compiler-verified because Xcode 27 is unavailable. Re-check availability and signatures with the shipping SDK.

## Contents

- [Durable Report Outbox](#durable-report-outbox)
- [Metric and Diagnostic Analysis](#metric-and-diagnostic-analysis)
- [Key Metric Result Catalog](#key-metric-result-catalog)
- [Call Stack Trees](#call-stack-trees)
- [Custom Signpost Metrics](#custom-signpost-metrics)
- [Extended Launch](#extended-launch)
- [iOS 26 Compatibility](#ios-26-compatibility)
- [Xcode Organizer](#xcode-organizer)
- [Apple Documentation](#apple-documentation)

## Durable Report Outbox

The report consumer should perform one small, reliable operation: encode and durably enqueue the complete report.

Use an outbox record that includes:

- encoded `MetricReport` or `DiagnosticReport` bytes
- report kind
- local schema version
- app version and build
- receipt timestamp
- stable deduplication key
- upload-attempt count and next-attempt timestamp

Keep raw reports until the server accepts them or a documented retention limit expires. Parse derived fields in a separate worker so a parser failure cannot discard the source evidence.

```swift
@available(iOS 27.0, *)
func enqueue(_ report: MetricReport) async throws {
    let data = try JSONEncoder().encode(report)
    try await outbox.insert(
        kind: .metric,
        payload: data,
        deduplicationKey: stableKey(for: report)
    )
}

@available(iOS 27.0, *)
func enqueue(_ report: DiagnosticReport) async throws {
    let data = try JSONEncoder().encode(report)
    try await outbox.insert(
        kind: .diagnostic,
        payload: data,
        deduplicationKey: stableKey(for: report)
    )
}
```

`outbox` and `stableKey(for:)` are application-owned abstractions. Build the key from stable report metadata and the encoded report rather than memory identity.

The upload worker should:

1. Read a bounded batch.
2. Upload with authentication and request-level idempotency.
3. Retry transient failures with exponential backoff and jitter.
4. Quarantine invalid records without blocking later records.
5. Delete or mark uploaded only after server acknowledgement.
6. Apply byte and age limits so telemetry cannot consume unbounded storage.

Do not rely on a modern backfill call. Apple's iOS 27 `MetricManager` documentation exposes the live `metricReports` and `diagnosticReports` sequences, not replacements for `pastPayloads` or `pastDiagnosticPayloads`.

## Metric and Diagnostic Analysis

### Daily metric reports

Use `MetricReport.timeRange` to establish the aggregation window. Treat `environment` as optional and retain the entire interval/state structure even if the first dashboard only uses `intervalEntries.fullDayEntry`.

```swift
@available(iOS 27.0, *)
func analyze(_ report: MetricReport) {
    let fullDay = report.intervalEntries.fullDayEntry

    for result in fullDay.values {
        switch result {
        case .hangTime(let value):
            recordHangTime(value, interval: report.timeRange)
        case .scrollHitchTime(let value):
            recordScrollHitchTime(value, interval: report.timeRange)
        case .cpuTime(let value):
            recordCPUTime(value, interval: report.timeRange)
        case .peakMemory(let value):
            recordPeakMemory(value, interval: report.timeRange)
        case .foregroundTermination(let value):
            recordForegroundTerminations(value, interval: report.timeRange)
        case .extendedLaunch(let value):
            recordExtendedLaunch(value, interval: report.timeRange)
        case .signpostInterval(let value):
            recordSignpostInterval(value, interval: report.timeRange)
        @unknown default:
            break // The raw encoded report remains in the outbox.
        }
    }
}
```

Metric reports are normally daily aggregates. Compare distributions across app versions, hardware, OS versions, and relevant environment fields. Avoid attributing a full-day value to one action without supporting local traces.

### Individual diagnostic reports

Process the report only after durable storage:

```swift
@available(iOS 27.0, *)
func analyze(_ report: DiagnosticReport) {
    switch report.result {
    case .crash(let crash):
        symbolicate(crash.callStackTree)
    case .hang(let hang):
        recordHang(hang.hangDuration)
        symbolicate(hang.callStackTree)
    case .cpuException(let exception):
        recordCPUException(
            totalCPUTime: exception.totalCPUTime,
            sampledTime: exception.totalSampledTime
        )
        symbolicate(exception.callStackTree)
    case .diskWriteException(let exception):
        recordDiskWriteException(exception.totalBytesWritten)
        symbolicate(exception.callStackTree)
    case .appLaunch(let launch):
        recordLaunchDiagnostic(launch.launchDuration)
        symbolicate(launch.callStackTree)
    case .memoryException(let memory):
        symbolicate(memory.callStackTree)
    @unknown default:
        break // Preserve and revisit the raw report after updating the parser.
    }
}
```

Diagnostics are event-based and intended for prompt delivery when the system produces them. They are not a complete ledger of all crashes, hangs, launches, or resource events.

## Key Metric Result Catalog

Load this catalog when mapping exact `MetricResult` cases into a parser or dashboard:

| Area | `MetricResult` cases |
|---|---|
| Responsiveness | `hangTime`, `hitchTime`, `scrollHitchTime` |
| Terminations | `foregroundTermination`, `backgroundTermination` |
| Runtime | `totalForegroundTime`, `totalBackgroundTime`, `totalBackgroundAudioTime`, `totalBackgroundLocationTime`, `locationActivityTime` |
| CPU and memory | `cpuTime`, `cpuInstructionsCount`, `peakMemory`, `suspendedMemory` |
| Network | `totalWiFiUpload`, `totalWiFiDownload`, `totalCellularUpload`, `totalCellularDownload`, `cellularConditionTime` |
| Launch | `timeToFirstDraw`, `applicationResumeTime`, `optimizedTimeToFirstDraw`, `extendedLaunch` |
| Storage | `logicalDiskWrites`, `totalFileCount`, `totalFileSize`, `totalDiskSpaceCapacity` |
| Display and GPU | `pixelLuminance`, `gpuTime`, `metalFrameRate` |
| Custom intervals | `signpostInterval` |

## Call Stack Trees

`CallStackTree` is Codable and retains the structure needed for later analysis. Keep the whole tree plus `binaryInfo` before producing flattened display frames.

Use `forEachFrame` when the consumer only needs frame traversal. Use `callStackThreads` when thread relationships matter. Symbolicate against the exact archive and dSYMs for the report's app build.

Recommended server-side pipeline:

1. Read the encoded diagnostic report.
2. Resolve the app version/build to its archive.
3. Match binary identifiers from `binaryInfo`.
4. Symbolicate offsets against the matching dSYMs.
5. Cluster signatures without deleting the original tree.

## Custom Signpost Metrics

Use the retained iOS 27 manager to create a log handle:

```swift
let log = manager.logHandle(category: "Database")

mxSignpost(.begin, log: log, name: "Migration")
await migrateDatabase()
mxSignpost(.end, log: log, name: "Migration")
```

The resulting aggregate is a `MetricResult.signpostInterval` value. Keep signpost category and name stable across releases so comparisons remain meaningful.

Prefer `mxSignpost` for MetricKit intervals that need resource measurements. Apple's documentation notes that `OSSignposter` intervals created with the MetricKit handle do not populate the same resource-measurement fields.

## Extended Launch

Track launch-critical work through the retained manager:

```swift
@MainActor
@available(iOS 27.0, *)
func loadLaunchData(using manager: MetricManager) async throws -> AppData {
    try await manager.trackLaunchTask(
        id: "load-app-data",
        onTrackingError: { error in
            recordLaunchTrackingError(error)
        }
    ) {
        try await loadAppData()
    }
}
```

The tracked closure's result and application error propagate normally. `onTrackingError` reports `MetricManager.LaunchTaskError` without replacing the closure's outcome. Keep `LaunchTaskID` values stable and do not track noncritical background work as launch work.

Extended launch results appear under `MetricResult.extendedLaunch`.

## iOS 26 Compatibility

Use this branch only for deployment targets that include iOS/iPadOS 26 or earlier supported versions. `MXMetricManager` is deprecated in iOS 27.

### Subscriber and past payloads

Register one retained subscriber as early as possible:

```swift
final class LegacyMetricsSubscriber: NSObject, MXMetricManagerSubscriber {
    static let shared = LegacyMetricsSubscriber()

    private override init() {
        super.init()
    }

    func start() {
        let manager = MXMetricManager.shared
        manager.add(self)

        // Legacy-only backfill APIs.
        persist(manager.pastPayloads)
        persist(manager.pastDiagnosticPayloads)
    }

    func didReceive(_ payloads: [MXMetricPayload]) {
        persist(payloads)
    }

    func didReceive(_ payloads: [MXDiagnosticPayload]) {
        persist(payloads)
    }

    private func persist(_ payloads: [MXMetricPayload]) {
        for payload in payloads {
            durableLegacyOutbox.enqueue(payload.jsonRepresentation())
        }
    }

    private func persist(_ payloads: [MXDiagnosticPayload]) {
        for payload in payloads {
            durableLegacyOutbox.enqueue(payload.jsonRepresentation())
        }
    }
}
```

The outbox calls above are application-owned placeholders. Make them durable before parsing or uploading. Prevent duplicate `add(_:)` calls in the app's lifecycle code.

Route at launch:

```swift
if #available(iOS 27.0, *) {
    modernMetricsService.start()
} else {
    LegacyMetricsSubscriber.shared.start()
}
```

### Legacy signposts

```swift
let log = MXMetricManager.makeLogHandle(category: "Database")

mxSignpost(.begin, log: log, name: "Migration")
await migrateDatabase()
mxSignpost(.end, log: log, name: "Migration")
```

Legacy signpost aggregates are available through `MXMetricPayload.signpostMetrics`.

### Legacy extended launch

```swift
try MXMetricManager.extendLaunchMeasurement(forTaskID: "load-app-data")
defer {
    try? MXMetricManager.finishExtendedLaunchMeasurement(forTaskID: "load-app-data")
}
await loadAppData()
```

Pair the calls on every control-flow path. Use `defer` where it can guarantee completion without changing asynchronous behavior.

## Xcode Organizer

Start with Organizer when Apple-provided aggregation is sufficient. A custom ingestion backend adds value when the product needs:

- correlations with feature flags, experiments, or backend incidents
- custom alert thresholds and retention
- cross-platform observability
- report-level symbolication and clustering
- export into an existing telemetry warehouse

Keep privacy and data-minimization requirements explicit. Avoid attaching user content or direct identifiers to MetricKit reports.

## Apple Documentation

- [MetricManager](https://sosumi.ai/documentation/metrickit/metricmanager)
- [metricReports](https://sosumi.ai/documentation/metrickit/metricmanager/metricreports)
- [diagnosticReports](https://sosumi.ai/documentation/metrickit/metricmanager/diagnosticreports)
- [MetricReport](https://sosumi.ai/documentation/metrickit/metricreport)
- [DiagnosticReport](https://sosumi.ai/documentation/metrickit/diagnosticreport)
- [MetricResult](https://sosumi.ai/documentation/metrickit/metricresult)
- [DiagnosticResult](https://sosumi.ai/documentation/metrickit/diagnosticresult)
- [CallStackTree](https://sosumi.ai/documentation/metrickit/callstacktree)
- [MetricManager.logHandle(category:)](https://sosumi.ai/documentation/metrickit/metricmanager/loghandle(category:))
- [Synchronous trackLaunchTask](https://sosumi.ai/documentation/metrickit/metricmanager/tracklaunchtask(id:ontrackingerror:_:)-48k2s)
- [Asynchronous trackLaunchTask](https://sosumi.ai/documentation/metrickit/metricmanager/tracklaunchtask(id:ontrackingerror:_:)-jnu1)
- [MXMetricManager](https://sosumi.ai/documentation/metrickit/mxmetricmanager)
- [iOS & iPadOS 27 release notes](https://sosumi.ai/documentation/ios-ipados-release-notes/ios-ipados-27-release-notes)
- [What's new in MetricKit (WWDC26)](https://sosumi.ai/videos/play/wwdc2026/222)
