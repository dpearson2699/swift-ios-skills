# MetricKit Boundary Routing

## Problem/Feature Description

A team reports that a SwiftUI feed stutters during development. Instruments shows hot body updates and layout churn. Product also wants production hang and crash telemetry to flow into the analytics backend with enough information for triage.

## Output Specification

Create `metrickit-boundaries.md` explaining what the MetricKit skill should handle directly and what should be routed to adjacent skills. The MetricKit-owned section must explicitly name iOS 27 `MetricManager` setup, `MetricReport` and `DiagnosticReport` ingestion, `HangDiagnostic` or `CrashDiagnostic` processing, durable backend export, and the isolated iOS 26 `MXMetricManager` compatibility path. Explicitly route Instruments capture, LLDB, Memory Graph, and `xctrace` workflow details to `debugging-instruments`; route SwiftUI invalidation/body/identity remediation to `swiftui-performance`. Include enough detail about `CallStackTree` symbolication and production telemetry delivery for engineers to route the work correctly. Keep the output concise and do not include a SwiftUI refactor or Instruments tutorial.
