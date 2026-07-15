---
name: energykit
description: "Query grid electricity forecasts and submit load events using EnergyKit to help users optimize home electricity usage. Use when building smart home apps, EV charger controls, HVAC scheduling, or energy management dashboards that guide users to use power during cleaner or cheaper grid periods."
---

# EnergyKit

Use grid cleanliness and cost guidance to shift or reduce managed-device load.
For managed-device insights, submit the device's real load events promptly.

> **Beta-sensitive.** Core EnergyKit ships in iOS/iPadOS 26. The iOS/iPadOS 27
> `ElectricalLoadDevice` and Home-facing LoadEvents experience are beta; re-check
> current Apple documentation before relying on those APIs.

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

### Entitlements and Version Split

| Runtime | Load-event device API | Capabilities |
|---|---|---|
| iOS/iPadOS 26.x | `deviceID:` compatibility initializer | EnergyKit |
| iOS/iPadOS 27+ beta | `ElectricalLoadDevice` with the `device:` initializer | EnergyKit; add EnergyKit LoadEvents for Home app integration |

All EnergyKit use requires `com.apple.developer.energykit`; enable the EnergyKit
capability on the app target. On iOS/iPadOS 27+, add the EnergyKit LoadEvents
capability (`com.apple.developer.energykit.loadevents-experience`) only when the
app needs device names, energy context, activity logs, historical charts, or
trend notifications in the Home app. That Home experience requires both
capabilities. Missing permission can surface as `EnergyKitError.permissionDenied`.

### Import

```swift
import EnergyKit
```

**Platform availability:** Core EnergyKit APIs are iOS/iPadOS 26.0+. Some
insight breakdown APIs, including grid cleanliness categories, are 26.1+ and
need availability guards. Apple currently documents electricity guidance only
for the contiguous United States; handle `EnergyKitError.unsupportedRegion`.

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
| `ElectricalLoadDevice` | iOS/iPadOS 27+ beta device identity for load events |
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
func submitEVBeginEvent(
    at venue: EnergyVenue,
    guidanceToken: UUID,
    deviceID: String,
    deviceName: String
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
        power: Measurement(value: 0, unit: .kilowatts),
        energy: Measurement(value: 0, unit: .kilowattHours)
    )

    let event: ElectricVehicleLoadEvent
    if #available(iOS 27.0, iPadOS 27.0, *) {
        let device = ElectricalLoadDevice(
            id: deviceID,
            name: deviceName,
            type: .electricVehicle
        )
        event = ElectricVehicleLoadEvent(
            timestamp: Date(), measurement: measurement,
            session: session, device: device
        )
    } else {
        // iOS/iPadOS 26 compatibility; deprecated in the iOS 27 SDK.
        event = ElectricVehicleLoadEvent(
            timestamp: Date(), measurement: measurement,
            session: session, deviceID: deviceID
        )
    }

    try await venue.submitEvents([event])
}
```

### HVAC Load Events

```swift
func submitHVACEvent(
    at venue: EnergyVenue,
    guidanceToken: UUID,
    stage: Int,
    deviceID: String,
    deviceName: String
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

    let event: ElectricHVACLoadEvent
    if #available(iOS 27.0, iPadOS 27.0, *) {
        let device = ElectricalLoadDevice(
            id: deviceID,
            name: deviceName,
            type: .hvac
        )
        event = ElectricHVACLoadEvent(
            timestamp: Date(), measurement: measurement,
            session: session, device: device
        )
    } else {
        // iOS/iPadOS 26 compatibility; deprecated in the iOS 27 SDK.
        event = ElectricHVACLoadEvent(
            timestamp: Date(), measurement: measurement,
            session: session, deviceID: deviceID
        )
    }

    try await venue.submitEvents([event])
}
```

### Session States

| State | When to Use |
|---|---|
| `.begin` | Device starts consuming electricity |
| `.active` | Device is actively consuming (periodic updates) |
| `.end` | Device stops consuming electricity |

Preserve `.begin → .active → .end` and submit events promptly rather than
holding long batches. For EV charging, submit `.begin` with zero power and
energy, `.active` about every 15 minutes plus significant changes, and `.end`
with zero power and cumulative energy. Retain unacknowledged events and retry
`EnergyKitError.rateLimitExceeded` with bounded backoff. Load the
[EV session manager](references/energykit-patterns.md#ev-charging-session-manager)
or [HVAC session manager](references/energykit-patterns.md#hvac-control-manager)
for device-specific lifecycle handling.

Only promise Home app device names, energy context, activity logs, charts, and
trend notifications on iOS/iPadOS 27+ when both the base EnergyKit and EnergyKit
LoadEvents capabilities are present.

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
| Assuming every region has guidance | Apple currently documents guidance only in the contiguous US; handle unsupported-region and unavailable venue/guidance states. |
| Fabricating or discarding the guidance token | Persist the real token on the requesting device and submit that token with its load events. |
| Sending isolated or delayed load samples | Preserve `.begin → .active → .end`, submit promptly, and retain events until submission succeeds. |
| Using `deviceID:` as the current default | Use iOS/iPadOS 27+ `ElectricalLoadDevice` and `device:`; keep `deviceID:` only for the 26.x runtime branch. |
| Using a hardcoded venue ID | Discover venues with `EnergyVenue.venues()` and select the intended venue. |

## Review Checklist

- [ ] Base EnergyKit capability is present; iOS/iPadOS 27+ Home integration also has EnergyKit LoadEvents
- [ ] Region, permission, venue discovery, unavailable guidance, and service errors are handled
- [ ] Real guidance tokens stay with the requesting device/app and its submitted load events
- [ ] iOS/iPadOS 27+ uses `ElectricalLoadDevice`/`device:`; `deviceID:` is isolated to 26.x compatibility
- [ ] `.begin → .active → .end` events follow device cadence, submit promptly, survive failure, and retry rate limits with bounded backoff
- [ ] Ratings/actions are interpreted correctly; insight options, availability, granularity, and minimum ranges match the UI
- [ ] MetricKit telemetry is not substituted for EnergyKit load events or insights

## References

- Extended workflows for app architecture, EV/HVAC session cadence, dashboard
  presentation, insights, errors, and venue discovery:
  [references/energykit-patterns.md](references/energykit-patterns.md)
- [EnergyKit framework](https://sosumi.ai/documentation/energykit)
- [ElectricityGuidance](https://sosumi.ai/documentation/energykit/electricityguidance)
- [ElectricityGuidance.Service](https://sosumi.ai/documentation/energykit/electricityguidance/service)
- [ElectricityGuidance.Query](https://sosumi.ai/documentation/energykit/electricityguidance/query)
- [ElectricityGuidance.Value](https://sosumi.ai/documentation/energykit/electricityguidance/value)
- [EnergyVenue](https://sosumi.ai/documentation/energykit/energyvenue)
- [ElectricalLoadDevice](https://sosumi.ai/documentation/energykit/electricalloaddevice)
- [ElectricVehicleLoadEvent](https://sosumi.ai/documentation/energykit/electricvehicleloadevent)
- [ElectricHVACLoadEvent](https://sosumi.ai/documentation/energykit/electrichvacloadevent)
- [ElectricityInsightService](https://sosumi.ai/documentation/energykit/electricityinsightservice)
- [ElectricityInsightRecord](https://sosumi.ai/documentation/energykit/electricityinsightrecord)
- [ElectricityInsightQuery](https://sosumi.ai/documentation/energykit/electricityinsightquery)
- [EnergyKitError](https://sosumi.ai/documentation/energykit/energykiterror)
- [EnergyKit entitlement](https://sosumi.ai/documentation/bundleresources/entitlements/com.apple.developer.energykit)
- [EnergyKit LoadEvents entitlement](https://sosumi.ai/documentation/bundleresources/entitlements/com.apple.developer.energykit.loadevents-experience)
- [Providing charging history for electric vehicles](https://sosumi.ai/documentation/energykit/providing-informative-charging-history-for-electric-vehicles)
- [Optimizing home electricity usage](https://sosumi.ai/documentation/energykit/optimizing-home-electricity-usage)
