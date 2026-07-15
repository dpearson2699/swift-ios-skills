# MetricKit Telemetry Setup Review

## Problem/Feature Description

An iOS team builds with the iOS 27 SDK but still deploys to iOS 26. Their draft creates `MetricManager` inside a SwiftUI dashboard, consumes only `metricReports`, uploads each report before saving it, and assumes `MetricManager.pastPayloads` can recover reports missed before the dashboard opens.

## Output Specification

Create `metrickit-telemetry-plan.md` with corrected iOS 27 guidance and a concise Swift sketch where useful. Cover the lifetime and consumption rules for both modern report sequences, durable-first persistence, and upload isolation. Explain the documented modern backfill limitation and provide a separate availability-gated iOS 26 compatibility path. Distinguish metric and diagnostic delivery behavior. Focus on production ingestion and avoid turning this into an Instruments tutorial.
