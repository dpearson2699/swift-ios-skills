---
name: energykit
description: "Query grid electricity forecasts and submit load events using EnergyKit to help users optimize home electricity usage. Use when building smart home apps, EV charger controls, HVAC scheduling, or energy management dashboards that guide users to use power during cleaner or cheaper grid periods."
---

# EnergyKit

Provide grid electricity forecasts to help users choose when to use electricity.
EnergyKit identifies times when grid electricity is relatively cleaner and,
when cost information is available, less expensive. Apps use that guidance to
shift or reduce managed device load.

> **Beta-sensitive.** EnergyKit is new in iOS 26 and may change before GM.
> Re-check current Apple documentation before relying on specific API details.

## Contents

- [Setup](#setup)
- [Core Concepts](#core-concepts)
- [Querying Electricity Guidance](#querying-electricity-guidance)
- [Working with Guidance Values](#working-with-guidance-values)
- [Energy Venues](#energy-venues)
- [Submitting Load Events](#submitting-load-events)
- [Electricity Insights](#electricity-insights)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

### Entitlement

EnergyKit requires the `com.apple.developer.energykit` entitlement. Enable the
EnergyKit capability in Xcode so the entitlement is added to the app target.
Treat this as a top-level setup prerequisite before writing guidance queries,
venue lookup, load-event submission, or insight code. Missing permission can
surface as `EnergyKitError.permissionDenied`.

### Import

```swift
import EnergyKit
```

**Platform availability:** Core EnergyKit APIs are iOS 26.0+ and iPadOS 26.0+.
Some insight breakdown APIs, including grid cleanliness categories, are iOS
26.1+ / iPadOS 26.1+ and need availability guards.

## Core Concepts

EnergyKit provides two main capabilities:

1. **Electricity Guidance** -- time-weighted forecasts telling apps when
   electricity is cleaner and, when rate data is available, less expensive
2. **Load Events** -- telemetry from managed devices (EV chargers, HVAC)
   submitted by the same device/app that requested guidance so EnergyKit can
   generate insights

### Key Types

| Type | Role |
|---|---|
| `ElectricityGuidance` | Forecast data with weighted time intervals |
| `ElectricityGuidance.Service` | Interface for obtaining guidance data |
| `ElectricityGuidance.Query` | Query specifying shift or reduce action |
| `ElectricityGuidance.Value` | A time interval with a rating (0.0-1.0) |
| `EnergyVenue` | A physical location (home) registered for energy management |
| `ElectricVehicleLoadEvent` | Load event for EV charger telemetry |
| `ElectricHVACLoadEvent` | Load event for HVAC system telemetry |
| `ElectricityInsightService` | Service for querying energy/runtime insights |
| `ElectricityInsightRecord` | Historical energy or runtime data, optionally broken down by tariff or 26.1+ grid cleanliness |
| `ElectricityInsightQuery` | Query for historical insight data |

### Suggested Actions

| Action | Use Case |
|---|---|
| `.shift` | Devices that can move consumption to a different time (EV charging) |
| `.reduce` | Devices that can lower consumption without stopping (HVAC setback) |

## Querying Electricity Guidance

Use `ElectricityGuidance.Service` to get a forecast stream for a venue.

```swift
import EnergyKit

func observeGuidance(venueID: UUID) async throws {
    let query = ElectricityGuidance.Query(suggestedAction: .shift)
    let service = ElectricityGuidance.sharedService

    let guidanceStream = service.guidance(using: query, at: venueID)

    for try await guidance in guidanceStream {
        print("Guidance token: \(guidance.guidanceToken)")
        print("Interval: \(guidance.interval)")
        print("Venue: \(guidance.energyVenueID)")

        // Check if rate plan information is available
        if guidance.options.contains(.guidanceIncorporatesRatePlan) {
            print("Rate plan data incorporated")
        }
        if guidance.options.contains(.locationHasRatePlan) {
            print("Location has a rate plan")
        }

        processGuidanceValues(guidance.values)
    }
}
```

## Working with Guidance Values

Each `ElectricityGuidance.Value` contains a time interval and a rating
from 0.0 to 1.0. Lower ratings indicate better times to use electricity.

```swift
func processGuidanceValues(_ values: [ElectricityGuidance.Value]) {
    for value in values {
        let interval = value.interval
        let rating = value.rating  // 0.0 (best) to 1.0 (worst)

        print("From \(interval.start) to \(interval.end): rating \(rating)")
    }
}

// Find the best time to charge
func bestChargingWindow(
    in values: [ElectricityGuidance.Value]
) -> ElectricityGuidance.Value? {
    values.min(by: { $0.rating < $1.rating })
}

// Find all "good" windows below a threshold
func goodWindows(
    in values: [ElectricityGuidance.Value],
    threshold: Double = 0.3
) -> [ElectricityGuidance.Value] {
    values.filter { $0.rating <= threshold }
}
```

### Displaying Guidance in SwiftUI

```swift
import SwiftUI
import EnergyKit

struct GuidanceTimelineView: View {
    let values: [ElectricityGuidance.Value]

    var body: some View {
        List(values, id: \.interval.start) { value in
            HStack {
                VStack(alignment: .leading) {
                    Text(value.interval.start, style: .time)
                    Text(value.interval.end, style: .time)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                RatingIndicator(rating: value.rating)
            }
        }
    }
}

struct RatingIndicator: View {
    let rating: Double

    var color: Color {
        if rating <= 0.3 { return .green }
        if rating <= 0.6 { return .yellow }
        return .red
    }

    var label: String {
        if rating <= 0.3 { return "Good" }
        if rating <= 0.6 { return "Fair" }
        return "Avoid"
    }

    var body: some View {
        Text(label)
            .padding(.horizontal)
            .padding(.vertical)
            .background(color.opacity(0.2))
            .foregroundStyle(color)
            .clipShape(Capsule())
    }
}
```

## Energy Venues

An `EnergyVenue` represents a physical location registered for energy management.

```swift
// List all venues
func listVenues() async throws -> [EnergyVenue] {
    try await EnergyVenue.venues()
}

// Get a specific venue by ID
func getVenue(id: UUID) async throws -> EnergyVenue {
    try await EnergyVenue.venue(for: id)
}

// Get a venue matching a HomeKit home
func getVenueForHome(homeID: UUID) async throws -> EnergyVenue {
    try await EnergyVenue.venue(matchingHomeUniqueIdentifier: homeID)
}
```

### Venue Properties

```swift
let venue = try await EnergyVenue.venue(for: venueID)
print("Venue ID: \(venue.id)")
print("Venue name: \(venue.name)")
```

## Submitting Load Events

Report device consumption data back to the system. This helps the system
generate electricity insights. The same EnergyKit-capable device/app that
requested electricity guidance must submit the corresponding load events, using
the guidance token returned by EnergyKit. Do not invent a token.

### EV Charger Load Events

```swift
func submitEVChargingEvent(
    at venue: EnergyVenue,
    guidanceToken: UUID,
    deviceID: String
) async throws {
    let session = ElectricVehicleLoadEvent.Session(
        id: UUID(),
        state: .begin,
        guidanceState: ElectricVehicleLoadEvent.Session.GuidanceState(
            wasFollowingGuidance: true,
            guidanceToken: guidanceToken
        )
    )

    let measurement = ElectricVehicleLoadEvent.ElectricalMeasurement(
        stateOfCharge: 45,
        direction: .imported,
        power: Measurement(value: 7.2, unit: .kilowatts),
        energy: Measurement(value: 0, unit: .kilowattHours)
    )

    let event = ElectricVehicleLoadEvent(
        timestamp: Date(),
        measurement: measurement,
        session: session,
        deviceID: deviceID
    )

    try await venue.submitEvents([event])
}
```

### HVAC Load Events

```swift
func submitHVACEvent(
    at venue: EnergyVenue,
    guidanceToken: UUID,
    stage: Int,
    deviceID: String
) async throws {
    let session = ElectricHVACLoadEvent.Session(
        id: UUID(),
        state: .active,
        guidanceState: ElectricHVACLoadEvent.Session.GuidanceState(
            wasFollowingGuidance: true,
            guidanceToken: guidanceToken
        )
    )

    let measurement = ElectricHVACLoadEvent.ElectricalMeasurement(stage: stage)

    let event = ElectricHVACLoadEvent(
        timestamp: Date(),
        measurement: measurement,
        session: session,
        deviceID: deviceID
    )

    try await venue.submitEvents([event])
}
```

### Session States

| State | When to Use |
|---|---|
| `.begin` | Device starts consuming electricity |
| `.active` | Device is actively consuming (periodic updates) |
| `.end` | Device stops consuming electricity |

For EV charging, record begin/end, one steady sample about every 15 minutes,
and extra samples for user actions, pauses, new guidance, or rapid power
changes. For HVAC, submit separate events when equipment starts, when heating
or cooling stage changes (heat stage 1 -> 2, heat -> cool, cool -> idle), and
when equipment stops. Batch events when practical for performance. Insights
are only available for submitted events, and load events for an `EnergyVenue`
are visible to people who share the associated Home in the Home app.

## Electricity Insights

Query historical energy and runtime data for devices using
`ElectricityInsightService`. An empty `ElectricityInsightQuery.Options` option
set returns totals only; it does not populate cleanliness or tariff breakdowns.
Request `.cleanliness` and/or `.tariff` only when the UI needs those breakdowns.
Do not substitute MetricKit app power metrics for EnergyKit insights; EnergyKit
insights depend on EnergyKit load events submitted for the managed device.

Choose insight granularity from the requested range. For a seven-day view,
query `.hourly`; use `.daily` only when the query covers at least a calendar
month.

```swift
func queryEnergyInsights(deviceID: String, venueID: UUID) async throws {
    let sevenDaysAgo = Calendar.current.date(
        byAdding: .day,
        value: -7,
        to: Date()
    )!

    let query = ElectricityInsightQuery(
        options: [.cleanliness, .tariff],
        range: DateInterval(
            start: sevenDaysAgo,
            end: Date()
        ),
        granularity: .hourly,
        flowDirection: .imported
    )

    let service = ElectricityInsightService.shared
    let stream = try await service.energyInsights(
        forDeviceID: deviceID, using: query, atVenue: venueID
    )

    for await record in stream {
        if let total = record.totalEnergy { print("Total: \(total)") }

        if #available(iOS 26.1, iPadOS 26.1, *),
           let cleaner = record.dataByGridCleanliness?.cleaner {
            print("Cleaner: \(cleaner)")
        }
    }
}
```

Use `runtimeInsights(forDeviceID:using:atVenue:)` for runtime data instead
of energy. Granularity options: `.hourly`, `.daily`, `.weekly`, `.monthly`,
`.yearly`. Choose a range that matches Apple's minimum aggregation windows:
hourly for at least a calendar week, daily for at least a calendar month,
weekly for at least six months, and monthly or yearly for at least a calendar
year. See [references/energykit-patterns.md](references/energykit-patterns.md) for full insight examples.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Querying before capability setup | Verify the EnergyKit entitlement and handle `.permissionDenied`. |
| Assuming every region has guidance | Handle unsupported-region, unavailable-venue/guidance, service, and rate-limit states. |
| Fabricating or discarding the guidance token | Persist the real token on the requesting device and submit that token with its load events. |
| Sending isolated load samples | Preserve `.begin → .active → .end` and Apple's event cadence. |
| Using a hardcoded venue ID | Discover venues with `EnergyVenue.venues()` and select the intended venue. |

## Review Checklist

- [ ] `com.apple.developer.energykit` entitlement added to the project
- [ ] `EnergyKitError.unsupportedRegion` handled with user-facing message
- [ ] `EnergyKitError.permissionDenied` handled gracefully
- [ ] Real guidance token stored and submitted by the same EnergyKit-capable device/app
- [ ] Venues discovered via `EnergyVenue.venues()` before querying guidance
- [ ] Load event sessions follow `.begin` -> `.active` -> `.end`, with Apple cadence and practical batching
- [ ] `ElectricityGuidance.Value.rating` interpreted correctly (lower is better)
- [ ] `SuggestedAction` matches the device type (`.shift` for EV, `.reduce` for HVAC)
- [ ] Insight queries use appropriate minimum ranges for their granularity
- [ ] Empty insight query options are treated as totals-only, not as cleanliness or tariff requests
- [ ] MetricKit power telemetry is not used as a substitute for EnergyKit load events or insights
- [ ] Grid cleanliness insight fields are guarded for iOS/iPadOS 26.1+
- [ ] Users understand load events are shared with people who share the Home
- [ ] Rate limiting handled via `EnergyKitError.rateLimitExceeded`
- [ ] Service unavailability handled with retry logic

## References

- Extended patterns (full app architecture, SwiftUI dashboard): [references/energykit-patterns.md](references/energykit-patterns.md)
- [EnergyKit framework](https://sosumi.ai/documentation/energykit)
- [ElectricityGuidance](https://sosumi.ai/documentation/energykit/electricityguidance)
- [ElectricityGuidance.Service](https://sosumi.ai/documentation/energykit/electricityguidance/service)
- [ElectricityGuidance.Query](https://sosumi.ai/documentation/energykit/electricityguidance/query)
- [ElectricityGuidance.Value](https://sosumi.ai/documentation/energykit/electricityguidance/value)
- [EnergyVenue](https://sosumi.ai/documentation/energykit/energyvenue)
- [ElectricVehicleLoadEvent](https://sosumi.ai/documentation/energykit/electricvehicleloadevent)
- [ElectricHVACLoadEvent](https://sosumi.ai/documentation/energykit/electrichvacloadevent)
- [ElectricityInsightService](https://sosumi.ai/documentation/energykit/electricityinsightservice)
- [ElectricityInsightRecord](https://sosumi.ai/documentation/energykit/electricityinsightrecord)
- [ElectricityInsightQuery](https://sosumi.ai/documentation/energykit/electricityinsightquery)
- [EnergyKitError](https://sosumi.ai/documentation/energykit/energykiterror)
- [Optimizing home electricity usage](https://sosumi.ai/documentation/energykit/optimizing-home-electricity-usage)
