# MetricKit Signpost And Extended Launch Correction

## Problem/Feature Description

A code review found this draft guidance in a MetricKit setup note:

```swift
let log = MXMetricManager.makeLogHandle(category: "network")
let signpostID = MXSignpostIntervalData.makeSignpostID(log: log)
mxSignpost(.begin, log: log, name: "DataFetch", signpostID: signpostID)
// work
mxSignpost(.end, log: log, name: "DataFetch", signpostID: signpostID)

MXMetricManager.extendLaunchMeasurement(forTaskID: "com.example.restore")
await restoreState()
MXMetricManager.finishExtendedLaunchMeasurement(forTaskID: "com.example.restore")
```

## Output Specification

Create `metrickit-api-corrections.md` for an app built with the iOS 27 SDK. Show the current `MetricManager` log-handle and `mxSignpost` pattern without allocating or passing a signpost ID, and name the current result surface. Replace the manual launch pair with the current tracked-launch API and explain its isolation, result/error, and tracking-error behavior. Identify which draft APIs belong only in an availability-gated iOS 26 compatibility branch.
